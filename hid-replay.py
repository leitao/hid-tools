#!/bin/env python3
# -*- coding: utf-8 -*-
#
# Hid tools / hid-replay.py
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
import sys
import time
import uhid
from parse import parse, findall


class HIDReplay(object):
    def __init__(self, filename):
        self._devices = {}
        self.filename = filename
        with open(filename) as f:
            idx = 0
            for l in f.readlines():
                l = l.strip()
                if l.startswith('D:'):
                    r = parse('D: {idx:d}', l)
                    assert r is not None
                    idx = r['idx']
                    continue
                if idx not in self._devices:
                    self._devices[idx] = uhid.UHIDDevice()
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
                    r = findall(' {:x}', " " + r['desc'])
                    dev.rdesc = [x[0] for x in r]
                    assert len(dev.rdesc) == length

        for d in self._devices.values():
            d.create_kernel_device()

    def destroy(self):
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
            for l in f.readlines():
                if l.startswith('D:'):
                    r = parse('D: {idx:d}', l)
                    assert r is not None
                    dev = self._devices[r['idx']]
                elif l.startswith('E:'):
                    r = parse('E: {sec:d}.{usec:d} {len:2d}{data}', l)
                    assert r is not None
                    length = r['len']
                    timestamp = r['sec'] + r['usec']/1000000
                    r = findall(' {:x}', r['data'])
                    data = [x[0] for x in r]
                    assert len(data) == int(length)
                    now = datetime.today()
                    if t is None:
                        t = now
                        timestamp_offset = timestamp
                    target_time = t + timedelta(seconds=timestamp - timestamp_offset)
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


def main(argv):
    try:
        replay = HIDReplay(argv[0])
        try:
            while uhid.UHIDDevice.process_one_event(1000):
                pass
            print('Hit enter (re)start replaying the events')
            sys.stdin.readline()
            replay.inject_events()
        except KeyboardInterrupt:
            pass
        replay.destroy()
    except PermissionError:
        print('Insufficient permissions, please run me as root.')


if __name__ == '__main__':
    main(sys.argv[1:])
