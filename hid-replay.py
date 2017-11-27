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


class HIDReplay(object):
    def __init__(self, filename):
        self._devices = {}
        self.filename = filename
        with open(filename) as f:
            idx = 0
            name = None
            rdesc = None
            phys = None
            info = None
            for l in f.readlines():
                if l.startswith('D:'):
                    idx = int(l.split(' ')[1])
                    name = None
                    rdesc = None
                    phys = None
                    info = None
                    continue
                if idx not in self._devices:
                    self._devices[idx] = uhid.UHIDDevice()
                dev = self._devices[idx]
                if l.startswith('N:'):
                    name = l.split(' ', 1)[1].strip()
                    dev.name = name
                elif l.startswith('I:'):
                    bus, vid, pid = l.split(' ')[1:]
                    info = [int(i, 16) for i in (bus, vid, pid)]
                    dev.info = info
                elif l.startswith('P:'):
                    phys = l.split(' ', 1)[1].strip()
                    dev.phys = phys
                elif l.startswith('R:'):
                    length, rdesc = l.split(' ', 2)[1:]
                    rdesc = [int(r, 16) for r in rdesc.split()]
                    assert int(length) == len(rdesc)
                    dev.rdesc = rdesc

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
                    idx = int(l.split(' ')[1])
                    dev = self._devices[idx]
                elif l.startswith('E:'):
                    data = l.split(' ', 1)[1]
                    timestamp, length, data = data.split(' ', 2)
                    timestamp = float(timestamp)
                    data = [int(d, 16) for d in data.split()]
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
        while uhid.UHIDDevice.process_one_event(1000):
            pass
        print('Hit enter (re)start replaying the events')
        sys.stdin.readline()
        replay.inject_events()
    finally:
        replay.destroy()


if __name__ == '__main__':
    main(sys.argv[1:])
