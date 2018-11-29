#!/bin/env python3
# -*- coding: utf-8 -*-
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

import hidtools.hid as hid # noqa
from hidtools.util import twos_comp, to_twos_comp # noqa
from hidtools.uhid import UHIDDevice  # noqa


class UHIDTestDevice(UHIDDevice):
    def __init__(self, name, rdesc_str=None, rdesc=None):
        if rdesc_str is None and rdesc is None:
            raise Exception('Please provide at least a rdesc or rdesc_str')
        super().__init__()
        self.name = name
        if not name.startswith('uhid test '):
            self.name = 'uhid test ' + self.name
        self.opened = False
        self.input_nodes = {}
        self._opened_files = []
        if rdesc is None:
            self.rdesc = hid.ReportDescriptor.from_human_descr(rdesc_str)
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
        elif 'ID_INPUT_KEY' in device.properties:
            type = 'Key'
        else:
            # abort, the device has not been processed by udev
            print('abort', devname, list(device.properties.items()))
            return

        event_node = open(devname, 'rb')
        self._opened_files.append(event_node)
        evdev = libevdev.Device(event_node)
        fd = evdev.fd.fileno()
        flag = fcntl.fcntl(fd, fcntl.F_GETFD)
        fcntl.fcntl(fd, fcntl.F_SETFL, flag | os.O_NONBLOCK)

        self.input_nodes[type] = evdev

    def open(self):
        self.opened = True

    def __del__(self):
        for evdev in self._opened_files:
            evdev.close()

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
        syn_event = libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
        key_event = libevdev.InputEvent(libevdev.EV_KEY)
        abs_event = libevdev.InputEvent(libevdev.EV_ABS)
        rel_event = libevdev.InputEvent(libevdev.EV_REL)
        msc_event = libevdev.InputEvent(libevdev.EV_MSC.MSC_SCAN)

        def assertInputEventsIn(self, expected_events, effective_events):
            effective_events = effective_events.copy()
            for ev in expected_events:
                self.assertIn(ev, effective_events)
                effective_events.remove(ev)
            return effective_events

        def assertInputEvents(self, expected_events, effective_events):
            r = self.assertInputEventsIn(expected_events, effective_events)
            self.assertEqual(len(r), 0)

        @classmethod
        def debug_reports(cls, reports, uhdev=None):
            data = [' '.join([f'{v:02x}' for v in r]) for r in reports]

            if uhdev is not None:
                human_data = [uhdev.parsed_rdesc.get_str(r, split_lines=True) for r in reports]
                try:
                    human_data = [f'\n\t       {" " * h.index("/")}'.join(h.split('\n')) for h in human_data]
                except ValueError:
                    # '/' not found: not a numbered report
                    human_data = [f'\n\t      '.join(h.split('\n')) for h in human_data]
                data = [f'{d}\n\t ====> {h}' for d, h in zip(data, human_data)]

            reports = data

            if len(reports) == 1:
                print(f'sending 1 report:')
            else:
                print(f'sending {len(reports)} reports:')
            for report in reports:
                print('\t', report)


def reload_udev_rules():
    import subprocess
    subprocess.run("udevadm control --reload-rules".split())
    subprocess.run("udevadm hwdb --update".split())


def create_udev_rule(uuid):
    os.makedirs('/run/udev/rules.d', exist_ok=True)
    with open(f'/run/udev/rules.d/91-uhid-test-device-REMOVEME-{uuid}.rules', 'w') as f:
        f.write('KERNELS=="*input*", ATTRS{name}=="uhid test *", ENV{LIBINPUT_IGNORE_DEVICE}="1"\n')
        f.write('KERNELS=="*input*", ATTRS{name}=="uhid test * System Multi Axis", ENV{ID_INPUT_TOUCHSCREEN}="", ENV{ID_INPUT_SYSTEM_MULTIAXIS}="1"\n')
    reload_udev_rules()


def teardown_udev_rule(uuid):
    os.remove(f'/run/udev/rules.d/91-uhid-test-device-REMOVEME-{uuid}.rules')
    reload_udev_rules()


def setUpModule():
    # create a udev rule to make libinput ignore the test devices
    if 'PYTEST_RUNNING' not in os.environ:
        create_udev_rule('XXXXX')


def tearDownModule():
    # clean up after ourselves
    if 'PYTEST_RUNNING' not in os.environ:
        teardown_udev_rule('XXXXX')


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
    from test_mouse import *  # noqa
    from test_multitouch import *  # noqa
    main(sys.argv[1:])
