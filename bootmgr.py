#!/usr/bin/env python3

import logging
import re
import shlex
import subprocess
from collections import OrderedDict
from copy import copy
from pathlib import Path

import toml


logger = logging.getLogger('bootmgr')


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


def first_number(s):
    '''Returns the index of the first number in a string.
    '''
    if s:
        for i, char in enumerate(s):
            if '0' <= char <= '9':
                return i
    return -1


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
        raise RuntimeException('could not identify the boot partition')
    return device[:idx], device[idx:]


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


def current_state():
    '''Gets the current boot entries by calling `efibootmgr`.
    '''
    proc = subprocess.run(['efibootmgr'], stdout=subprocess.PIPE, encoding='utf-8', check=True)
    state = proc.stdout
    return parse_state(state)


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

    def __init__(self, path, device=None, partition=None):
        '''Initializes the manager from some configuration file.
        '''
        if device is partition is None:
            device, partition = find_device(path)
        assert device is not None and partition is not None

        self.path = path
        self.device = device
        self.partition = partition
        self.cfg = toml.load(path, OrderedDict)
        self.state = current_state()

    def execute(self, cmd):
        '''Executes an efibootmgr command.
        '''
        cmd = [shlex.quote(arg) for arg in cmd]
        cmd_str = " ".join(cmd)
        logger.info(f'calling: {cmd_str}')
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, encoding='utf-8', check=True)
        state = proc.stdout
        self.state = parse_state(state)
        return self.state

    def update(self, label):
        '''Updates the boot entry of the given label to match the config.
        '''
        params = copy(self.cfg[label])
        loader = params.pop('loader')
        cmd = [
            'efibootmgr',
            '--disk', self.device,
            '--part', self.partition,
            '--label', label,
            '--loader', loader,
            '--unicode', dump(params),
        ]
        if label in self.state:
            cmd += ['--bootnum', self.state[label]]
        else:
            cmd += ['--create']
        return self.execute(cmd)

    def delete(self, label):
        '''Deletes the boot entry with the given label.
        '''
        cmd = [
            'efibootmgr',
            '--bootnum', self.state[label],
            '--delete-bootnum',
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
        return self.state


def main(path):
    logging.basicConfig(level='DEBUG')
    bootmgr = BootMgr(path)
    return bootmgr.sync()
