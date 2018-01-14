#!/usr/bin/env python3

import argparse
import logging
import re
import sys

from collections import OrderedDict
from subprocess import run, PIPE
from pathlib import Path

import toml


__version__ = 'bootmgr v1.0.0-dev'
logger = logging.getLogger('bootmgr')


def first_number(s):
    '''Returns the index of the first number in a string.
    '''
    if s:
        for i, char in enumerate(s):
            if '0' <= char <= '9':
                return i
    return -1


def iter_mounts():
    '''Iterate over active mounts by parsing `/proc/mounts`.

    Yields:
        dev: The path to the device.
        mount: The path to the mount point.
    '''
    with open('/proc/mounts', 'r') as f:
        for line in f:
            fields = line.split()
            if fields[0].startswith('/dev'):
                dev = fields[0]
                mount = fields[1].replace('\\040', ' ')
                yield dev, mount


def find_device(path):
    '''Get the device and partition on which a file lives.

    Returns:
        dev: The device, e.g. '/dev/sda' if the file lives on /dev/sda1.
        part: The partition, e.g. '1' if the file lives on /dev/sda1.
    '''
    device = None
    prefix = ''
    path = str(path)
    for dev, mount in iter_mounts():
        if path.startswith(mount) and len(prefix) < len(mount):
            prefix = mount
            device = dev
    idx = first_number(device)
    if idx < 1:
        raise RuntimeError('Could not identify the partition')
    return device[:idx], device[idx:]


def find_config():
    '''Search for the `bootmgr.toml`.
    '''
    paths = {
        '/boot/efi/bootmgr.toml',
        '/boot/bootmgr.toml',
        '/bootmgr.toml',
    }
    for p in paths:
        if Path(p).exists():
            return p
    raise RuntimeError('Could not find bootmgr.toml')


def dump(params):
    '''Serialize a dictionary of kernel parameters to a string.
    '''
    params = _dump(params)
    params = list(params)
    params = ' '.join(params)
    return params

def _dump(params, prefix=''):
    for k, v in params.items():
        if v is True:
            yield f'{prefix}{k}'
        elif v is False:
            yield f'{prefix}no{k}'
        elif hasattr(v, 'items'):
            for v in _dump(v, prefix=f'{k}.'):
                yield v
        else:
            yield f'{prefix}{k}={v}'


def parse_efibootmgr(proc):
    '''Parse the output of `efibootmgr`.
    '''
    entries = OrderedDict()
    order = []

    patterns = {
        'order': re.compile('BootOrder: ((.{4},?)*)'),
        'entry': re.compile('Boot(.{4})[* ] (.+)'),
    }

    for line in proc.stdout.split('\n'):
        for kind, pattern in patterns.items():
            m = pattern.match(line)

            if m and kind == 'order':
                order = m[1].split(',')

            elif m and kind == 'entry':
                entry = m[1]
                label = m[2]
                entries[label] = entry

    for bootnum in order:
        for label, entry in entries.items():
            if entry == bootnum:
                entries.move_to_end(label)
                break

    return entries


class BootMgr:
    '''A class for managing EFI boot entries.
    '''

    def __init__(self, path, device=None, partition=None, full_delete=False):
        '''Initializes the manager from some configuration file.
        '''
        if device is partition is None:
            device, partition = find_device(path)
        assert device is not None and partition is not None

        self.path = path
        self.device = device
        self.partition = partition
        self.full_delete = full_delete
        self.cfg = OrderedDict()
        self.state = OrderedDict()

        self.read_config(path)
        self.read_state()

    def read_config(self, path):
        '''Read boot entries from a file and merge with the current config.
        '''
        cfg = toml.load(path, OrderedDict)
        self.cfg.update(cfg)
        return self.cfg

    def read_state(self):
        '''Read the current boot entries from the EFI variables.
        '''
        cmd = ['efibootmgr']
        self.execute(cmd)
        return self.state

    def sync(self):
        '''Syncronizes the boot entries with the config.
        '''
        logger.info('Syncing boot entries...')
        labels = set(self.state) | set(self.cfg)
        for label in labels:
            if label in self.cfg:
                self.update(label)
            else:
                self.delete(label)
        self.fix_order()
        return self

    def update(self, label):
        '''Updates the boot entry of the given label to match the config.
        '''
        params = self.cfg[label].copy()
        loader = params.pop('loader')
        cmd = [
            'efibootmgr',
            '--label', label,
            '--loader', loader,
            '--unicode', dump(params),
        ]

        if label in self.state:
            logger.info(f"Updating entry '{label}'")
            cmd += ['--bootnum', self.state[label], '--active']

        else:
            logger.info(f"Creating entry '{label}'")
            cmd += ['--create']

        self.execute(cmd)
        return self

    def delete(self, label, full_delete=None):
        '''Deletes the boot entry with the given label.
        '''
        if full_delete is None:
            full_delete = self.full_delete

        if full_delete:
            logger.info(f"Deleting entry '{label}'")
            cmd = [
                'efibootmgr',
                '--bootnum', self.state[label],
                '--delete-bootnum',
            ]

        else:
            logger.info(f"Deactivating entry '{label}'")
            cmd = [
                'efibootmgr',
                '--bootnum', self.state[label],
                '--inactive',
            ]

        self.execute(cmd)
        return self

    def fix_order(self):
        '''Sets the boot order to match the config.
        '''
        logger.info('Setting boot order')
        order = ','.join(self.state[label] for label in self.cfg)
        cmd = ['efibootmgr', '--bootorder', order]
        self.execute(cmd)
        return self

    def execute(self, cmd):
        '''Executes an efibootmgr command.
        '''
        # No funny business
        assert cmd[0] == 'efibootmgr'

        # Ensure all commands target the right partition.
        cmd += ['--disk', self.device]
        cmd += ['--part', self.partition]

        # All efibootmgr commands print the new state to stdout.
        logger.debug(f'calling {cmd}')
        proc = run(cmd, stdout=PIPE, stderr=PIPE, encoding='utf-8')

        # Wrap errors from the subprocess for consistency.
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr)

        self.state = parse_efibootmgr(proc)
        return proc


def main(path=None, disk=None, part=None, delete=False, verbose=False):
    log_level = 'INFO' if verbose else 'WARN'
    logging.basicConfig(format='{message}', style='{', level=log_level)

    try:
        if path is None: path = find_config()
        bootmgr = BootMgr(path, device=disk, partition=part, full_delete=delete)
        bootmgr.sync()
        sys.exit(0)

    except Exception as e:
        logger.error(str(e))
        sys.exit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=False, description='Sync EFI boot entries with bootmgr.toml')

    group = parser.add_argument_group('Global Options')
    group.add_argument('-h', '--help', action='help', help='Print this help message and exit.')
    group.add_argument('-V', '--version', action='version', version=__version__, help='Print the version and exit.')
    group.add_argument('-v', '--verbose', action='store_true', help='Log actions to stderr.')
    group.add_argument('-D', '--delete', action='store_true', help='Delete entries which are not listed in the config.')
    group.add_argument('-d', '--disk', nargs=1, help='Override the disk containing the loaders.')
    group.add_argument('-p', '--part', nargs=1, help='Override the partition containing the loaders.')
    group.add_argument('path', nargs='?', metavar='PATH', help='Override the path to the config.')

    args = parser.parse_args()
    args = vars(args)
    main(**args)
