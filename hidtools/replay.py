#!/bin/env python3
# -*- coding: utf-8 -*-
#
# Hid tools / replay.py
#
# Copyright (c) 2017 Benjamin Tissoires <benjamin.tissoires@gmail.com>
# Copyright (c) 2017 Red Hat, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from datetime import datetime, timedelta
import argparse
import sys
import time
import hidtools.uhid
from parse import parse, findall

import logging
logging.basicConfig(format='%(levelname)s: %(name)s: %(message)s',
                    level=logging.INFO)
base_logger = logging.getLogger('hid')
logger = logging.getLogger('hid.replay')


class HIDReplay(object):
    def __init__(self, filename):
        self._devices = {}
        self.filename = filename
        self.replayed_count = 0
        with open(filename) as f:
            idx = 0
            for l in f:
                l = l.strip()
                if l.startswith('D:'):
                    r = parse('D: {idx:d}', l)
                    assert r is not None
                    idx = r['idx']
                    continue
                if idx not in self._devices:
                    self._devices[idx] = hidtools.uhid.UHIDDevice()
                dev = self._devices[idx]
                if l.startswith('N:'):
                    r = parse('N: {name}', l)
                    assert r is not None
                    dev.name = r['name']
                elif l.startswith('I:'):
                    r = parse('I: {bus:x} {vid:x} {pid:x}', l)
                    assert r is not None
                    dev.info = [r['bus'], r['vid'], r['pid']]
                elif l.startswith('P:'):
                    r = parse('P: {phys}', l)
                    if r is not None:
                        dev.phys = r['phys']
                elif l.startswith('R:'):
                    r = parse('R: {length:d} {desc}', l)
                    assert r is not None
                    length = r['length']
                    dev.rdesc = r['desc']
                    assert len(dev.rdesc) == length

        for d in self._devices.values():
            d.create_kernel_device()

    @property
    def ready(self):
        for d in self._devices.values():
            if not d.has_evdev_node:
                return False
        return True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        for d in self._devices.values():
            d.destroy()

    def inject_events(self, wait_max_seconds=2):
        t = None
        timestamp_offset = 0
        with open(self.filename) as f:
            idx = 0
            dev = None
            if idx in self._devices:
                dev = self._devices[idx]
            for l in f:
                if l.startswith('D:'):
                    r = parse('D: {idx:d}', l)
                    assert r is not None
                    dev = self._devices[r['idx']]
                elif l.startswith('E:'):
                    r = parse('E: {sec:d}.{usec:d} {len:2d}{data}', l)
                    assert r is not None
                    length = r['len']
                    timestamp = r['sec'] + r['usec'] / 1000000
                    r_ = findall(' {:S}', r['data'])
                    data = [int(x[0], 16) for x in r_]
                    assert len(data) == int(length)
                    now = datetime.today()
                    if t is None:
                        t = now
                        timestamp_offset = timestamp
                    target_time = t + timedelta(seconds=timestamp - timestamp_offset)
                    sleep = 0
                    if target_time > now:
                        sleep = target_time - now
                        sleep = sleep.seconds + sleep.microseconds / 1000000
                    if sleep < 0.01:
                        pass
                    elif sleep < wait_max_seconds:
                        time.sleep(sleep)
                    else:
                        t = now
                        timestamp_offset = timestamp
                        time.sleep(wait_max_seconds)
                    dev.call_input_event(data)
        self.replayed_count += 1

    def start_injecting_event(self):
        sys.stdin.readline()
        self.inject_events()

    def replay_one_sequence(self, wait=False):
        if not wait:
            self.inject_events()
            return
        count = self.replayed_count
        hidtools.uhid.UHIDDevice.append_fd_to_poll(sys.stdin.fileno(),
                                                   self.start_injecting_event)
        re = '' if count == 0 else 're'
        print(f'Hit enter to {re}start replaying the events')
        while count == self.replayed_count:
                hidtools.uhid.UHIDDevice.process_one_event(None)
        hidtools.uhid.UHIDDevice.remove_fd_from_poll(sys.stdin.fileno())


def main():
    parser = argparse.ArgumentParser(description='Replay a HID recording')
    parser.add_argument('recording', metavar='recording.hid',
                        type=str, help='Path to device recording')
    parser.add_argument('--verbose', action='store_true',
                        default=False, help='Show debugging information')
    args = parser.parse_args()
    if args.verbose:
        base_logger.setLevel(logging.DEBUG)

    try:
        with HIDReplay(args.recording) as replay:
            while hidtools.uhid.UHIDDevice.process_one_event(1000):
                if replay.ready:
                    break
            while True:
                replay.replay_one_sequence(wait=True)
    except PermissionError:
        print('Insufficient permissions, please run me as root.')
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    if sys.version_info < (3, 6):
        sys.exit('Python 3.6 or later required')

    main()
