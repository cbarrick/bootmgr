#!/usr/bin/env python3

import argparse
import logging
import re
from collections import OrderedDict
from copy import copy
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


def parse_state(state):
    '''Parse the output of `efibootmgr`.
    '''
    entries = OrderedDict()
    entry_pat = re.compile('Boot([0-9a-fA-F]{4})\*? (.+)')
    for line in state.split('\n'):
        match = entry_pat.match(line)
        if match:
            entry = match[1]
            label = match[2]
            entries[label] = entry
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
        self.cfg = toml.load(path, OrderedDict)
        self.state = OrderedDict()

        self.check_state()

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

        state = proc.stdout
        self.state = parse_state(state)
        return proc

    def check_state(self):
        '''Checks the current state of the boot entries.
        '''
        cmd = ['efibootmgr']
        return self.execute(cmd)

    def update(self, label):
        '''Updates the boot entry of the given label to match the config.
        '''
        params = copy(self.cfg[label])
        loader = params.pop('loader')
        cmd = [
            'efibootmgr',
            '--label', label,
            '--loader', loader,
            '--unicode', dump(params),
        ]
        if label in self.state:
            cmd += ['--bootnum', self.state[label], '--active']
        else:
            cmd += ['--create']
        return self.execute(cmd)

    def delete(self, label):
        '''Deletes the boot entry with the given label.
        '''
        if self.full_delete:
            cmd = [
                'efibootmgr',
                '--bootnum', self.state[label],
                '--delete-bootnum',
            ]
        else:
            cmd = [
                'efibootmgr',
                '--bootnum', self.state[label],
                '--inactive',
            ]
        return self.execute(cmd)

    def fix_order(self):
        '''Sets the boot order to match the config.
        '''
        order = ','.join(self.state[label] for label in self.cfg)
        cmd = ['efibootmgr', '--bootorder', order]
        return self.execute(cmd)

    def sync(self):
        '''Syncronizes the boot entries with the config.
        '''
        labels = set(self.state.keys()) | set(self.cfg.keys())
        for label in labels:
            if label in self.cfg:
                self.update(label)
            else:
                self.delete(label)
        self.fix_order()
        return self.check_state()


def main(path=None, disk=None, part=None, delete=False, verbose=False):
    log_level = 'INFO' if verbose else 'WARN'
    log_format = '{levelname} {message}'
    logging.basicConfig(format=log_format, style='{', level=log_level)

    try:
        if path is None: path = find_config()
        bootmgr = BootMgr(path, device=disk, partition=part, full_delete=delete)
        bootmgr.sync()
        proc = bootmgr.check_state()
        print(proc.stdout, end='')
        exit(0)

    except Exception as e:
        logger.error(str(e))
        exit(1)


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
