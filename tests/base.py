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

import logging
logger = logging.getLogger('hidtools.test.base')

import hidtools.hid as hid # noqa
from hidtools.util import twos_comp, to_twos_comp # noqa
from hidtools.uhid import UHIDDevice  # noqa


class UHIDTestDevice(UHIDDevice):
    def __init__(self, name, application, rdesc_str=None, rdesc=None, info=None):
        if rdesc_str is None and rdesc is None:
            raise Exception('Please provide at least a rdesc or rdesc_str')
        super().__init__()
        if name is None:
            name = f'uhid test {self.__class__.__name__}'
        if info is None:
            info = (3, 1, 2)
        self.name = name
        self.info = info
        self.default_reportID = None
        if not name.startswith('uhid test '):
            self.name = 'uhid test ' + self.name
        self.opened = False
        self.application = application
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
        to_remove = []
        for name, evdev in self.input_nodes.items():
            evdev.fd.close()
            to_remove.append(name)

        for name in to_remove:
            del(self.input_nodes[name])

    def next_sync_events(self):
        return list(self.evdev.events())

    @property
    def evdev(self):
        if self.application not in self.input_nodes:
            return None

        return self.input_nodes[self.application]


def skipIfUHDev(condition, reason):
    def decorator(func):
        func.skip_test_if_uhdev = condition
        func.skip_test_if_uhdev_reason = reason
        return func
    return decorator


class BaseTestCase:
    class ContextTest(unittest.TestCase):
        """A unit test where setUp/tearDown are amalgamated into a
        single generator

        see https://stackoverflow.com/questions/13874859/python-with-statement-and-its-use-in-a-class"""
        def context(self):
            """Put both setUp and tearDown code in this generator method
            with a single `yield` between"""
            yield

        def setUp(self):
            self.__context = self.context()
            next(self.__context)
        def tearDown(self):
            for _ in self.__context:
                raise RuntimeError("context method should only yield once")

    class TestUhid(ContextTest):
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
            remaining = self.assertInputEventsIn(expected_events, effective_events)
            self.assertEqual(remaining, [])

        @classmethod
        def debug_reports(cls, reports, uhdev=None, events=None):
            data = [' '.join([f'{v:02x}' for v in r]) for r in reports]

            if uhdev is not None:
                human_data = [uhdev.parsed_rdesc.format_report(r, split_lines=True) for r in reports]
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

            if events is not None:
                print('events received:', events)

        def create_device(self):
            raise Exception('please reimplement me in subclasses')

        def assertName(self, uhdev):
            self.assertEqual(uhdev.evdev.name, uhdev.name)

        def _skip_conditions(self, udev):
            method = getattr(self, self._testMethodName)
            try:
                skip_test_if_uhdev = method.skip_test_if_uhdev
            except AttributeError:
                return

            if skip_test_if_uhdev(self.uhdev):
                self.skipTest(method.skip_test_if_uhdev_reason)

        def context(self):
            with self.create_device() as self.uhdev:
                self._skip_conditions(self.uhdev)
                self.uhdev.create_kernel_device()
                while self.uhdev.application not in self.uhdev.input_nodes:
                    self.uhdev.dispatch(10)
                self.assertIsNotNone(self.uhdev.evdev)
                yield

        def test_creation(self):
            """Make sure the device gets processed by the kernel and creates
            the expected application input node.

            If this fail, there is something wrong in the device report
            descriptors."""
            uhdev = self.uhdev
            self.assertName(uhdev)
            self.assertEqual(len(uhdev.next_sync_events()), 0)
            uhdev.destroy()
            while uhdev.opened:
                if uhdev.dispatch(100) == 0:
                    break
            with self.assertRaises(OSError):
                uhdev.evdev.fd.read()


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
