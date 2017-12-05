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

import hid  # noqa
from uhid import UHIDDevice  # noqa


def twos_comp(val, bits):
    """compute the 2's compliment of int value val"""
    if (val & (1 << (bits - 1))) != 0:
        val = val - (1 << bits)
    return val


def to_twos_comp(val, bits):
    return val & ((1 << bits) - 1)


class UHIDTest(UHIDDevice):
    def __init__(self, name, rdesc_str=None, rdesc=None):
        if rdesc_str is None and rdesc is None:
            raise Exception('Please provide at least a rdesc or rdesc_str')
        super(UHIDTest, self).__init__()
        self.name = name
        self.opened = False
        self.input_nodes = {}
        if rdesc is None:
            self.rdesc = hid.ReportDescriptor.from_rdesc_str(rdesc_str)
        else:
            self.rdesc = rdesc

    def udev_event(self, event):
        if event.action != 'add':
            return

        device = event

        if 'DEVNAME' not in device.properties:
            return

        devname = device.properties['DEVNAME']
        if not devname.startswith('/dev/input/event'):
            return

        # associate the Input type to the matching HID application
        # we reuse the guess work from udev
        type = None
        if 'ID_INPUT_TOUCHSCREEN' in device.properties:
            type = 'Touch Screen'
        elif 'ID_INPUT_TOUCHPAD' in device.properties:
            type = 'Touch Pad'
        elif 'ID_INPUT_TABLET' in device.properties:
            type = 'Pen'
        elif 'ID_INPUT_MOUSE' in device.properties:
            type = 'Mouse'
        else:
            # abort, the device has not been processed by udev
            print('abort', devname, list(device.properties.items()))
            return

        event_node = open(devname, 'rb')
        evdev = libevdev.Device(event_node)
        fd = evdev.fd.fileno()
        flag = fcntl.fcntl(fd, fcntl.F_GETFD)
        fcntl.fcntl(fd, fcntl.F_SETFL, flag | os.O_NONBLOCK)

        self.input_nodes[type] = evdev

    def open(self):
        self.opened = True

    def __exit__(self, *exc_details):
        for evdev in self.input_nodes.values():
            evdev.fd.close()
        super(UHIDTest, self).__exit__(*exc_details)

    def close(self):
        self.opened = False

    def start(self, flags):
        pass

    def stop(self):
        for name, evdev in self.input_nodes.items():
            evdev.fd.close()
            del(self.input_nodes[name])

    def get_report(self, req, rnum, rtype):
        self.call_get_report(req, [], 1)

    def set_report(self, req, rnum, rtype, size, data):
        self.call_set_report(req, 1)

    def next_sync_events(self):
        return list(self.evdev.events())

    @property
    def evdev(self):
        if len(self.input_nodes) == 0:
            return None

        # return the 'first' input node
        return self.input_nodes[list(self.input_nodes.keys())[0]]


class BaseTestCase:
    class TestUhid(unittest.TestCase):
        syn_event = libevdev.InputEvent('EV_SYN', 'SYN_REPORT', 0)
        key_event = libevdev.InputEvent("EV_KEY")
        abs_event = libevdev.InputEvent("EV_ABS")
        rel_event = libevdev.InputEvent("EV_REL")
        msc_event = libevdev.InputEvent("EV_MSC", "MSC_SCAN")

        def assertInputEventsIn(self, expected_events, effective_events):
            effective_events = effective_events.copy()
            for ev in expected_events:
                self.assertIn(ev, effective_events)
                effective_events.remove(ev)
            return effective_events

        def assertInputEvents(self, expected_events, effective_events):
            r = self.assertInputEventsIn(expected_events, effective_events)
            self.assertEqual(len(r), 0)


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
