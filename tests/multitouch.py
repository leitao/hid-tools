#!/bin/env python3
# -*- coding: utf-8 -*-
#
# Hid tools / tests/multitouch.py: unittest for multitouch devices
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

import base
import libevdev
import sys
import unittest
from base import main, setUpModule, tearDownModule  # noqa


class Touch(object):
    def __init__(self, id, x, y):
        self.contactid = id
        self.x = x
        self.y = y
        self.cx = x
        self.cy = y
        self.tipswitch = True
        self.confidence = True
        self.pressure = 100
        self.azimuth = 0
        self.inrange = True
        self.width = 10
        self.height = 10


class Pen(Touch):
    def __init__(self, x, y):
        super(Pen, self).__init__(0, x, y)
        self.barrel = False
        self.invert = False
        self.eraser = False
        self.x_tilt = False
        self.y_tilt = False
        self.twist = 0


class Digitizer(base.UHIDTest):
    @classmethod
    def msCertificationBlob(cls, reportID):
        return f'''
        Usage Page (Digitizers)
        Usage (Touch Screen)
        Collection (Application)
         Report ID ({reportID})
         Usage Page (0xff00)
         Usage (0xc5)
         Logical Minimum (0)
         Logical Maximum (255)
         Report Size (8)
         Report Count (256)
         Feature (Data,Var,Abs)
        End Collection
    '''

    def __init__(self, name, rdesc_str=None, rdesc=None):
        super(Digitizer, self).__init__("uhid test simple", rdesc_str, rdesc)
        self.info = 3, 1, 2
        self.scantime = 0
        self.max_contacts = 1
        logical_max = 0
        contact_max_found = False
        for item in self.parsed_rdesc.rdesc_items:
            descr = item.get_human_descr(0)[0]
            if 'Contact Max' in descr:
                contact_max_found = True
            elif 'Logical Maximum' in descr:
                logical_max = item.value
            elif 'Feature' in descr and contact_max_found:
                self.max_contacts = logical_max
                break
        # self.parsed_rdesc.dump(sys.stdout)
        self.create_kernel_device()

    def event(self, slots):
        self.scantime += 1
        self.contactcount = len(slots)
        r = self.format_report(reportID=1, data=slots)
        self.call_input_event(r)
        return r


class MinWin8TSParallel(Digitizer):
    def __init__(self, max_slots):
        self.max_slots = max_slots
        self.phys_max = 120, 90
        rdesc_finger_str = f'''
            Usage Page (Digitizers)
            Usage (Finger)
            Collection (Logical)
             Report Size (1)
             Report Count (1)
             Logical Minimum (0)
             Logical Maximum (1)
             Usage (Tip Switch)
             Input (Data,Var,Abs)
             Report Size (7)
             Logical Maximum (127)
             Input (Cnst,Var,Abs)
             Report Size (8)
             Logical Maximum (255)
             Usage (Contact Id)
             Input (Data,Var,Abs)
             Report Size (16)
             Unit Exponent (-1)
             Unit (Centimeter,SILinear)
             Logical Maximum (4095)
             Physical Minimum (0)
             Physical Maximum ({self.phys_max[0]})
             Usage Page (Generic Desktop)
             Usage (X)
             Input (Data,Var,Abs)
             Physical Maximum ({self.phys_max[1]})
             Usage (Y)
             Input (Data,Var,Abs)
            End Collection
'''
        rdesc_str = f'''
           Usage Page (Digitizers)
           Usage (Touch Screen)
           Collection (Application)
            Report ID (1)
            {rdesc_finger_str * self.max_slots}
            Unit Exponent (-4)
            Unit (Seconds,SILinear)
            Logical Maximum (65535)
            Physical Maximum (65535)
            Usage Page (Digitizers)
            Usage (Scan Time)
            Input (Data,Var,Abs)
            Report Size (8)
            Logical Maximum (255)
            Usage (Contact Count)
            Input (Data,Var,Abs)
            Report ID (2)
            Logical Maximum ({self.max_slots})
            Usage (Contact Max)
            Feature (Data,Var,Abs)
          End Collection
          {Digitizer.msCertificationBlob(68)}
'''
        super(MinWin8TSParallel, self).__init__("uhid test simple",
                                                rdesc_str)


class ElanXPS9360(Digitizer):
    def __init__(self):
        rdesc = "X 05 0d 09 04 a1 01 85 01 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 20 0d 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 50 07 46 a6 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 20 0d 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 50 07 46 a6 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 20 0d 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 50 07 46 a6 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 20 0d 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 50 07 46 a6 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 20 0d 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 50 07 46 a6 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 20 0d 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 50 07 46 a6 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 20 0d 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 50 07 46 a6 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 20 0d 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 50 07 46 a6 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 20 0d 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 50 07 46 a6 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 20 0d 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 50 07 46 a6 00 09 31 81 02 b4 c0 05 0d 09 56 55 00 65 00 27 ff ff ff 7f 95 01 75 20 81 02 09 54 25 7f 95 01 75 08 81 02 85 0a 09 55 25 0a b1 02 85 44 06 00 ff 09 c5 15 00 26 ff 00 75 08 96 00 01 b1 02 c0 06 ff 01 09 01 a1 01 85 02 15 00 26 ff 00 75 08 95 40 09 00 81 02 c0 06 00 ff 09 01 a1 01 85 03 75 08 95 1f 09 01 91 02 c0 06 01 ff 09 01 a1 01 85 04 15 00 26 ff 00 75 08 95 13 09 00 81 02 c0"
        super(ElanXPS9360, self).__init__("uhid test ElanXPS9360",
                                          rdesc=rdesc)


class BaseTest:
    class TestMultitouch(base.BaseTestCase.TestUhid):
        def __init__(self, methodName='runTest'):
            super(BaseTest.TestMultitouch, self).__init__(methodName)
            self.__create_device = self._create_device

        @classmethod
        def _debug_reports(cls, reports):
            if len(reports) == 1:
                print(f'sending 1 report: {reports[0]}')
            else:
                print(f'sending {len(reports)} reports:')
                for report in reports:
                    print('\t', report)

        def _create_device(self):
            raise Exception("please reimplement me in subclasses")

        def test_mt_creation(self):
            with self.__create_device() as uhdev:
                while not uhdev.opened:
                    uhdev.process_one_event(100)
                self.assertIsNotNone(uhdev.evdev)
                self.assertEqual(uhdev.evdev.name, uhdev.name)
                self.assertEqual(uhdev.evdev.num_slots, uhdev.max_contacts)
                self.assertEqual(len(uhdev.next_sync_events()), 0)

                uhdev.destroy()
                while uhdev.opened:
                    if uhdev.process_one_event(100) == 0:
                        break
                with self.assertRaises(OSError):
                    uhdev.evdev.fd.read()

        def test_mt_single_touch(self):
            with self.__create_device() as uhdev:
                while not uhdev.opened:
                    uhdev.process_one_event(100)

                t0 = Touch(1, 5, 10)
                r = uhdev.event([t0])
                events = uhdev.next_sync_events()
                self.assertIn(libevdev.InputEvent("EV_KEY", 'BTN_TOUCH', 1), events)
                self.assertEqual(uhdev.evdev.slot_value(0, 'ABS_MT_TRACKING_ID'), 0)
                self.assertEqual(uhdev.evdev.slot_value(0, 'ABS_MT_POSITION_X'), 5)
                self.assertEqual(uhdev.evdev.slot_value(0, 'ABS_MT_POSITION_Y'), 10)

                t0.tipswitch = False
                r = uhdev.event([t0])
                events = uhdev.next_sync_events()
                self.assertIn(libevdev.InputEvent("EV_KEY", 'BTN_TOUCH', 0), events)
                self.assertEqual(uhdev.evdev.slot_value(0, 'ABS_MT_TRACKING_ID'), -1)

                uhdev.destroy()

        def test_mt_dual_touch(self):
            with self.__create_device() as uhdev:
                while not uhdev.opened:
                    uhdev.process_one_event(100)

                t0 = Touch(1, 5, 10)
                t1 = Touch(2, 15, 20)
                r = uhdev.event([t0])
                events = uhdev.next_sync_events()
                self.assertIn(libevdev.InputEvent("EV_KEY", 'BTN_TOUCH', 1), events)
                self.assertEqual(uhdev.evdev.event_value("EV_KEY", "BTN_TOUCH"), 1)
                self.assertEqual(uhdev.evdev.slot_value(0, 'ABS_MT_TRACKING_ID'), 0)
                self.assertEqual(uhdev.evdev.slot_value(0, 'ABS_MT_POSITION_X'), 5)
                self.assertEqual(uhdev.evdev.slot_value(0, 'ABS_MT_POSITION_Y'), 10)
                self.assertEqual(uhdev.evdev.slot_value(1, 'ABS_MT_TRACKING_ID'), -1)

                r = uhdev.event([t0, t1])
                events = uhdev.next_sync_events()
                self.assertNotIn(libevdev.InputEvent("EV_KEY", 'BTN_TOUCH', 0), events)
                self.assertEqual(uhdev.evdev.event_value("EV_KEY", "BTN_TOUCH"), 1)
                self.assertNotIn(libevdev.InputEvent("EV_ABS", 'ABS_MT_POSITION_X', 5), events)
                self.assertNotIn(libevdev.InputEvent("EV_ABS", 'ABS_MT_POSITION_Y', 10), events)
                self.assertEqual(uhdev.evdev.slot_value(0, 'ABS_MT_TRACKING_ID'), 0)
                self.assertEqual(uhdev.evdev.slot_value(0, 'ABS_MT_POSITION_X'), 5)
                self.assertEqual(uhdev.evdev.slot_value(0, 'ABS_MT_POSITION_Y'), 10)
                self.assertEqual(uhdev.evdev.slot_value(1, 'ABS_MT_TRACKING_ID'), 1)
                self.assertEqual(uhdev.evdev.slot_value(1, 'ABS_MT_POSITION_X'), 15)
                self.assertEqual(uhdev.evdev.slot_value(1, 'ABS_MT_POSITION_Y'), 20)

                t0.tipswitch = False
                r = uhdev.event([t0, t1])
                events = uhdev.next_sync_events()
                self.assertEqual(uhdev.evdev.slot_value(0, 'ABS_MT_TRACKING_ID'), -1)
                self.assertEqual(uhdev.evdev.slot_value(1, 'ABS_MT_TRACKING_ID'), 1)
                self.assertNotIn(libevdev.InputEvent("EV_ABS", 'ABS_MT_POSITION_X'), events)
                self.assertNotIn(libevdev.InputEvent("EV_ABS", 'ABS_MT_POSITION_Y'), events)

                t1.tipswitch = False
                r = uhdev.event([t1])
                events = uhdev.next_sync_events()
                self.assertEqual(uhdev.evdev.slot_value(0, 'ABS_MT_TRACKING_ID'), -1)
                self.assertEqual(uhdev.evdev.slot_value(1, 'ABS_MT_TRACKING_ID'), -1)

                uhdev.destroy()


class TestMinWin8TSParallelDual(BaseTest.TestMultitouch):
    def _create_device(self):
        return MinWin8TSParallel(2)

class TestMinWin8TSParallel(BaseTest.TestMultitouch):
    def _create_device(self):
        return MinWin8TSParallel(10)

class TestElanXPS9360(BaseTest.TestMultitouch):
    def _create_device(self):
        return ElanXPS9360()


if __name__ == "__main__":
    main(sys.argv[1:])
