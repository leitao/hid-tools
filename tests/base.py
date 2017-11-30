#!/bin/env python3
# -*- coding: utf-8 -*-
#
# Hid tools / tests/base.py: base tools for unittest devices
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

import argparse
import fcntl
import libevdev
import os
import resource
import sys
import unittest

# FIXME: this is really wrong :)
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)) + '/..')

from uhid import UHIDDevice  # noqa


def twos_comp(val, bits):
    """compute the 2's compliment of int value val"""
    if (val & (1 << (bits - 1))) != 0:
        val = val - (1 << bits)
    return val


def to_twos_comp(val, bits):
    return val & ((1 << bits) - 1)


class UHIDTest(UHIDDevice):
    def __init__(self, name):
        super(UHIDTest, self).__init__()
        self.name = name
        self.opened = False
        self.evdev = None

    def open(self):
        self.opened = True
        # FIXME: we should handle more than one evdev node per uhid device
        if self.evdev is not None:
            return
        for c in self.udev.children:
            if 'DEVNAME' not in c.properties:
                continue
            devname = c.properties['DEVNAME']
            if devname.startswith('/dev/input/event'):
                self.evdev = libevdev.Libevdev()
                self.evdev.fd = open(devname, 'rb')
                fd = self.evdev.fd.fileno()
                flag = fcntl.fcntl(fd, fcntl.F_GETFD)
                fcntl.fcntl(fd, fcntl.F_SETFL, flag | os.O_NONBLOCK)

    def __exit__(self, *exc_details):
        if self.evdev is not None:
            self.evdev.fd.close()
        super(UHIDTest, self).__exit__(*exc_details)

    def close(self):
        self.opened = False

    def start(self, flags):
        pass

    def stop(self):
        if self.evdev is not None:
            self.evdev.fd.close()
            self.evdev = None

    def get_report(self, req, rnum, rtype):
        self.call_get_report(req, [], 1)

    def next_sync_events(self):
        events = []
        e = self.evdev.next_event()
        while e is not None:
            events.append(e)
            if e.matches("EV_SYN", "SYN_REPORT"):
                break
            e = self.evdev.next_event()
        return events


def setUpModule():
    # FIXME: setup udev rule to ignore our own uhid nodes
    pass


def tearDownModule():
    # FIXME: teardown udev rule to ignore our own uhid nodes
    pass


def parse(input_string):
    global run_ratbagctl_in_subprocess
    parser_test = argparse.ArgumentParser("Testsuite for hid devices")
    ns, rest = parser_test.parse_known_args(input_string)
    return rest


def main(argv):
    if not os.geteuid() == 0:
        sys.exit('Script must be run as root')

    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    args = parse(argv)

    unittest.main(argv=[sys.argv[0], *args])


if __name__ == '__main__':
    from mouse import *  # noqa
    from multitouch import *  # noqa
    main(sys.argv[1:])
