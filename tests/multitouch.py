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
import parse
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

    def __init__(self, name, rdesc_str=None, rdesc=None, application='Touch Screen'):
        super(Digitizer, self).__init__("uhid test simple", rdesc_str, rdesc)
        self.info = 3, 1, 2
        self.scantime = 0
        self.max_contacts = 1
        self.report_ids = {}
        self.application = application
        usage = None
        application = None
        logical_max = 0
        report_ids = {}

        # retrieve some info from the devices:
        # - the applications associated to each input report
        # - the contact max
        for item in self.parsed_rdesc.rdesc_items:
            descr = item.get_human_descr(0)[0]
            if 'Usage (' in descr:
                r = parse.parse('Usage ({usage})', descr)
                assert(r is not None)
                usage = r['usage']
            elif 'Collection (Application)' in descr:
                application = usage
            elif 'Report ID' in descr:
                try:
                    report_ids[application].append(item.value)
                except KeyError:
                    report_ids[application] = [item.value]
            elif 'Logical Maximum' in descr:
                logical_max = item.value
            elif 'Feature' in descr and usage == 'Contact Max':
                self.max_contacts = logical_max
                if self.max_contacts > 200:
                    self.max_contacts = 10

        # we have alist of possible report ID per application,
        # now filter out the ones associated with the input reports
        for application in report_ids:
            for id in report_ids[application]:
                if id in self.parsed_rdesc.reports:
                    self.report_ids[application] = id
                    break

        # self.parsed_rdesc.dump(sys.stdout)
        self.create_kernel_device()

    def event(self, slots):
        self.scantime += 1
        rs = []
        # make sure we have only the required number of available slots
        slots = slots[:self.max_contacts]
        self.contactcount = len(slots)

        while len(slots):
            r = self.format_report(reportID=self.report_ids[self.application], data=slots)
            self.call_input_event(r)
            rs.append(r)
            self.contactcount = 0
        return rs


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
        super(MinWin8TSParallel, self).__init__(f"uhid test parallel {self.max_slots}",
                                                rdesc_str)


class MinWin8TSHybrid(Digitizer):
    def __init__(self):
        self.max_slots = 10
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
            {rdesc_finger_str * 2}
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
        super(MinWin8TSHybrid, self).__init__("uhid test hybrid",
                                              rdesc_str)


class BaseTest:
    class TestMultitouch(base.BaseTestCase.TestUhid):
        def __init__(self, methodName='runTest'):
            super(BaseTest.TestMultitouch, self).__init__(methodName)
            self.__create_device = self._create_device

        @classmethod
        def _debug_reports(cls, reports):
            if len(reports) == 1:
                print(f'sending 1 report: {" ".join([f"{v:02x}" for v in reports[0]])}')
            else:
                print(f'sending {len(reports)} reports:')
                for report in reports:
                    print('\t', " ".join([f'{v:02x}' for v in report]))

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
                self.assertNotIn(libevdev.InputEvent("EV_KEY", 'BTN_TOUCH'), events)
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

        def test_mt_triple_tap(self):
            with self.__create_device() as uhdev:
                if uhdev.max_contacts <= 2:
                    uhdev.destroy()
                    raise unittest.SkipTest('Device not compatible')
                while not uhdev.opened:
                    uhdev.process_one_event(100)

                t0 = Touch(1, 5, 10)
                t1 = Touch(2, 15, 20)
                t2 = Touch(3, 25, 30)
                r = uhdev.event([t0, t1, t2])
                events = uhdev.next_sync_events()
                self.assertEqual(uhdev.evdev.slot_value(0, 'ABS_MT_TRACKING_ID'), 0)
                self.assertEqual(uhdev.evdev.slot_value(0, 'ABS_MT_POSITION_X'), 5)
                self.assertEqual(uhdev.evdev.slot_value(0, 'ABS_MT_POSITION_Y'), 10)
                self.assertEqual(uhdev.evdev.slot_value(1, 'ABS_MT_TRACKING_ID'), 1)
                self.assertEqual(uhdev.evdev.slot_value(1, 'ABS_MT_POSITION_X'), 15)
                self.assertEqual(uhdev.evdev.slot_value(1, 'ABS_MT_POSITION_Y'), 20)
                self.assertEqual(uhdev.evdev.slot_value(2, 'ABS_MT_TRACKING_ID'), 2)
                self.assertEqual(uhdev.evdev.slot_value(2, 'ABS_MT_POSITION_X'), 25)
                self.assertEqual(uhdev.evdev.slot_value(2, 'ABS_MT_POSITION_Y'), 30)

                t0.tipswitch = False
                t1.tipswitch = False
                t2.tipswitch = False
                r = uhdev.event([t0, t1, t2])
                events = uhdev.next_sync_events()
                self.assertEqual(uhdev.evdev.slot_value(0, 'ABS_MT_TRACKING_ID'), -1)
                self.assertEqual(uhdev.evdev.slot_value(1, 'ABS_MT_TRACKING_ID'), -1)
                self.assertEqual(uhdev.evdev.slot_value(2, 'ABS_MT_TRACKING_ID'), -1)

                uhdev.destroy()

        def test_mt_max_contact(self):
            with self.__create_device() as uhdev:
                while not uhdev.opened:
                    uhdev.process_one_event(100)

                touches = [Touch(i, i * 10, i * 10 + 5) for i in range(uhdev.max_contacts)]
                r = uhdev.event(touches)
                events = uhdev.next_sync_events()
                for i, t in enumerate(touches):
                    self.assertEqual(uhdev.evdev.slot_value(i, 'ABS_MT_TRACKING_ID'), i)
                    self.assertEqual(uhdev.evdev.slot_value(i, 'ABS_MT_POSITION_X'), t.x)
                    self.assertEqual(uhdev.evdev.slot_value(i, 'ABS_MT_POSITION_Y'), t.y)

                for t in touches:
                    t.tipswitch = False

                r = uhdev.event(touches)
                events = uhdev.next_sync_events()
                for i, t in enumerate(touches):
                    self.assertEqual(uhdev.evdev.slot_value(i, 'ABS_MT_TRACKING_ID'), -1)

                uhdev.destroy()


class TestMinWin8TSParallelDual(BaseTest.TestMultitouch):
    def _create_device(self):
        return MinWin8TSParallel(2)


class TestMinWin8TSParallel(BaseTest.TestMultitouch):
    def _create_device(self):
        return MinWin8TSParallel(10)


class TestMinWin8TSHybrid(BaseTest.TestMultitouch):
    def _create_device(self):
        return MinWin8TSHybrid()


class TestElanXPS9360(BaseTest.TestMultitouch):
    def _create_device(self):
        return Digitizer("uhid test ElanXPS9360", rdesc="X 05 0d 09 04 a1 01 85 01 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 20 0d 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 50 07 46 a6 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 20 0d 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 50 07 46 a6 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 20 0d 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 50 07 46 a6 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 20 0d 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 50 07 46 a6 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 20 0d 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 50 07 46 a6 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 20 0d 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 50 07 46 a6 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 20 0d 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 50 07 46 a6 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 20 0d 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 50 07 46 a6 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 20 0d 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 50 07 46 a6 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 20 0d 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 50 07 46 a6 00 09 31 81 02 b4 c0 05 0d 09 56 55 00 65 00 27 ff ff ff 7f 95 01 75 20 81 02 09 54 25 7f 95 01 75 08 81 02 85 0a 09 55 25 0a b1 02 85 44 06 00 ff 09 c5 15 00 26 ff 00 75 08 96 00 01 b1 02 c0 06 ff 01 09 01 a1 01 85 02 15 00 26 ff 00 75 08 95 40 09 00 81 02 c0 06 00 ff 09 01 a1 01 85 03 75 08 95 1f 09 01 91 02 c0 06 01 ff 09 01 a1 01 85 04 15 00 26 ff 00 75 08 95 13 09 00 81 02 c0")


class Test3m_0596_051c(BaseTest.TestMultitouch):
    def _create_device(self):
        return Digitizer("uhid test 3m_0596_051c", rdesc="728 05 01 09 01 a1 01 85 01 09 01 a1 00 05 09 09 01 95 01 75 01 15 00 25 01 81 02 95 07 75 01 81 03 95 01 75 08 81 03 05 01 09 30 09 31 15 00 26 ff 7f 35 00 46 ff 7f 95 02 75 10 81 02 c0 a1 02 15 00 26 ff 00 09 01 95 39 75 08 81 03 c0 c0 05 0d 09 0e a1 01 85 11 09 23 a1 02 09 52 09 53 15 00 25 0a 75 08 95 02 b1 02 c0 c0 09 04 a1 01 85 13 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 81 03 09 47 81 02 95 05 81 03 75 08 09 51 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 d1 12 81 02 09 31 46 b2 0b 81 02 06 00 ff 75 10 95 02 09 01 81 02 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 81 03 09 47 81 02 95 05 81 03 75 08 09 51 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 d1 12 81 02 09 31 46 b2 0b 81 02 06 00 ff 75 10 95 02 09 01 81 02 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 81 03 09 47 81 02 95 05 81 03 75 08 09 51 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 d1 12 81 02 09 31 46 b2 0b 81 02 06 00 ff 75 10 95 02 09 01 81 02 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 81 03 09 47 81 02 95 05 81 03 75 08 09 51 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 d1 12 81 02 09 31 46 b2 0b 81 02 06 00 ff 75 10 95 02 09 01 81 02 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 81 03 09 47 81 02 95 05 81 03 75 08 09 51 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 d1 12 81 02 09 31 46 b2 0b 81 02 06 00 ff 75 10 95 02 09 01 81 02 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 81 03 09 47 81 02 95 05 81 03 75 08 09 51 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 d1 12 81 02 09 31 46 b2 0b 81 02 06 00 ff 75 10 95 02 09 01 81 02 c0 05 0d 09 54 95 01 75 08 15 00 25 14 81 02 05 0d 55 0c 66 01 10 35 00 47 ff ff 00 00 27 ff ff 00 00 75 10 95 01 09 56 81 02 05 0d 09 55 85 12 15 00 25 14 75 08 95 01 b1 02 85 44 06 00 ff 09 c5 15 00 26 ff 00 75 08 96 00 01 b1 02 06 00 ff 15 00 26 ff 00 85 03 09 01 75 08 95 07 b1 02 85 04 09 01 75 08 95 17 b1 02 85 05 09 01 75 08 95 47 b1 02 85 06 09 01 75 08 95 07 b1 02 85 73 09 01 75 08 95 07 b1 02 85 08 09 01 75 08 95 07 b1 02 85 09 09 01 75 08 95 3f b1 02 85 0f 09 01 75 08 96 07 02 b1 02 c0")


class Testadvanced_silicon_04e8_2084(BaseTest.TestMultitouch):
    def _create_device(self):
        return Digitizer("uhid test advanced_silicon_04e8_2084", rdesc="721 05 0d 09 04 a1 01 85 01 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 c0 14 81 02 46 ae 0b 09 31 81 02 45 00 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 c0 14 81 02 46 ae 0b 09 31 81 02 45 00 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 c0 14 81 02 46 ae 0b 09 31 81 02 45 00 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 c0 14 81 02 46 ae 0b 09 31 81 02 45 00 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 c0 14 81 02 46 ae 0b 09 31 81 02 45 00 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 c0 14 81 02 46 ae 0b 09 31 81 02 45 00 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 c0 14 81 02 46 ae 0b 09 31 81 02 45 00 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 c0 14 81 02 46 ae 0b 09 31 81 02 45 00 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 c0 14 81 02 46 ae 0b 09 31 81 02 45 00 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 c0 14 81 02 46 ae 0b 09 31 81 02 45 00 c0 05 0d 15 00 27 ff ff 00 00 75 10 95 01 09 56 81 02 25 0a 75 08 09 54 81 02 85 44 09 55 b1 02 85 44 06 00 ff 09 c5 26 ff 00 96 00 01 b1 02 85 f0 09 01 95 04 b1 02 85 f2 09 03 b1 02 09 04 b1 02 09 05 b1 02 95 01 09 06 b1 02 09 07 b1 02 85 f1 09 02 95 07 91 02 85 f3 09 08 95 3d b1 02 c0")


class Testadvanced_silicon_2149_2306(BaseTest.TestMultitouch):
    def _create_device(self):
        return Digitizer("uhid test advanced_silicon_2149_2306", rdesc="411 05 0d 09 04 a1 01 85 01 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 f6 13 81 02 46 40 0b 09 31 81 02 45 00 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 f6 13 81 02 46 40 0b 09 31 81 02 45 00 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 f6 13 81 02 46 40 0b 09 31 81 02 45 00 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 f6 13 81 02 46 40 0b 09 31 81 02 45 00 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 f6 13 81 02 46 40 0b 09 31 81 02 45 00 c0 05 0d 15 00 27 ff ff 00 00 75 10 95 01 09 56 81 02 25 0a 75 08 09 54 81 02 85 44 09 55 b1 02 85 44 06 00 ff 09 c5 26 ff 00 96 00 01 b1 02 85 f0 09 01 95 04 81 02 85 f2 09 03 b1 02 09 04 b1 02 09 05 b1 02 95 01 09 06 b1 02 09 07 b1 02 85 f1 09 02 95 07 91 02 85 f3 09 08 95 3d b1 02 c0")


class Testadvanced_silicon_2149_230a(BaseTest.TestMultitouch):
    def _create_device(self):
        return Digitizer("uhid test advanced_silicon_2149_230a", rdesc="411 05 0d 09 04 a1 01 85 01 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 f6 13 81 02 46 40 0b 09 31 81 02 45 00 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 f6 13 81 02 46 40 0b 09 31 81 02 45 00 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 f6 13 81 02 46 40 0b 09 31 81 02 45 00 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 f6 13 81 02 46 40 0b 09 31 81 02 45 00 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 f6 13 81 02 46 40 0b 09 31 81 02 45 00 c0 05 0d 15 00 27 ff ff 00 00 75 10 95 01 09 56 81 02 25 0a 75 08 09 54 81 02 85 44 09 55 b1 02 85 44 06 00 ff 09 c5 26 ff 00 96 00 01 b1 02 85 f0 09 01 95 04 81 02 85 f2 09 03 b1 02 09 04 b1 02 09 05 b1 02 95 01 09 06 b1 02 09 07 b1 02 85 f1 09 02 95 07 91 02 85 f3 09 08 95 3d b1 02 c0")


class Testadvanced_silicon_2149_231c(BaseTest.TestMultitouch):
    def _create_device(self):
        return Digitizer("uhid test advanced_silicon_2149_231c", rdesc="411 05 0d 09 04 a1 01 85 01 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 e2 13 81 02 46 32 0b 09 31 81 02 45 00 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 e2 13 81 02 46 32 0b 09 31 81 02 45 00 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 e2 13 81 02 46 32 0b 09 31 81 02 45 00 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 e2 13 81 02 46 32 0b 09 31 81 02 45 00 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 e2 13 81 02 46 32 0b 09 31 81 02 45 00 c0 05 0d 15 00 27 ff ff 00 00 75 10 95 01 09 56 81 02 25 0a 75 08 09 54 81 02 85 44 09 55 b1 02 85 44 06 00 ff 09 c5 26 ff 00 96 00 01 b1 02 85 f0 09 01 95 04 b1 02 85 f2 09 03 b1 02 09 04 b1 02 09 05 b1 02 95 01 09 06 b1 02 09 07 b1 02 85 f1 09 02 95 07 91 02 85 f3 09 08 95 3d b1 02 c0")


class Testadvanced_silicon_2149_2703(BaseTest.TestMultitouch):
    def _create_device(self):
        return Digitizer("uhid test advanced_silicon_2149_2703", rdesc="411 05 0d 09 04 a1 01 85 01 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 66 17 81 02 46 34 0d 09 31 81 02 45 00 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 66 17 81 02 46 34 0d 09 31 81 02 45 00 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 66 17 81 02 46 34 0d 09 31 81 02 45 00 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 66 17 81 02 46 34 0d 09 31 81 02 45 00 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 66 17 81 02 46 34 0d 09 31 81 02 45 00 c0 05 0d 15 00 27 ff ff 00 00 75 10 95 01 09 56 81 02 25 0a 75 08 09 54 81 02 85 44 09 55 b1 02 85 44 06 00 ff 09 c5 26 ff 00 96 00 01 b1 02 85 f0 09 01 95 04 81 02 85 f2 09 03 b1 02 09 04 b1 02 09 05 b1 02 95 01 09 06 b1 02 09 07 b1 02 85 f1 09 02 95 07 91 02 85 f3 09 08 95 3d b1 02 c0")


class Testadvanced_silicon_2149_270b(BaseTest.TestMultitouch):
    def _create_device(self):
        return Digitizer("uhid test advanced_silicon_2149_270b", rdesc="411 05 0d 09 04 a1 01 85 01 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 52 17 81 02 46 20 0d 09 31 81 02 45 00 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 52 17 81 02 46 20 0d 09 31 81 02 45 00 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 52 17 81 02 46 20 0d 09 31 81 02 45 00 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 52 17 81 02 46 20 0d 09 31 81 02 45 00 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 52 17 81 02 46 20 0d 09 31 81 02 45 00 c0 05 0d 15 00 27 ff ff 00 00 75 10 95 01 09 56 81 02 25 0a 75 08 09 54 81 02 85 44 09 55 b1 02 85 44 06 00 ff 09 c5 26 ff 00 96 00 01 b1 02 85 f0 09 01 95 04 b1 02 85 f2 09 03 b1 02 09 04 b1 02 09 05 b1 02 95 01 09 06 b1 02 09 07 b1 02 85 f1 09 02 95 07 91 02 85 f3 09 08 95 3d b1 02 c0")


class Testadvanced_silicon_2619_5610(BaseTest.TestMultitouch):
    def _create_device(self):
        return Digitizer("uhid test advanced_silicon_2619_5610", rdesc="743 05 0d 09 04 a1 01 85 01 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 a1 00 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 f9 15 81 02 46 73 0c 09 31 81 02 45 00 c0 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 a1 00 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 f9 15 81 02 46 73 0c 09 31 81 02 45 00 c0 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 a1 00 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 f9 15 81 02 46 73 0c 09 31 81 02 45 00 c0 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 a1 00 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 f9 15 81 02 46 73 0c 09 31 81 02 45 00 c0 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 a1 00 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 f9 15 81 02 46 73 0c 09 31 81 02 45 00 c0 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 a1 00 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 f9 15 81 02 46 73 0c 09 31 81 02 45 00 c0 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 a1 00 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 f9 15 81 02 46 73 0c 09 31 81 02 45 00 c0 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 a1 00 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 f9 15 81 02 46 73 0c 09 31 81 02 45 00 c0 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 a1 00 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 f9 15 81 02 46 73 0c 09 31 81 02 45 00 c0 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 02 81 03 09 51 25 1f 75 05 95 01 81 02 a1 00 05 01 26 ff 7f 75 10 55 0e 65 11 09 30 35 00 46 f9 15 81 02 46 73 0c 09 31 81 02 45 00 c0 c0 05 0d 15 00 27 ff ff 00 00 75 10 95 01 09 56 81 02 25 0a 75 08 09 54 81 02 85 44 09 55 b1 02 85 44 06 00 ff 09 c5 26 ff 00 96 00 01 b1 02 85 f0 09 01 95 04 81 02 85 f2 09 03 b1 02 09 04 b1 02 09 05 b1 02 95 01 09 06 b1 02 09 07 b1 02 85 f1 09 02 95 07 91 02 c0")


class Testatmel_03eb_8409(BaseTest.TestMultitouch):
    def _create_device(self):
        return Digitizer("uhid test atmel_03eb_8409", rdesc="639 05 0d 09 04 a1 01 85 01 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 01 81 03 95 01 81 03 25 1f 75 05 09 51 81 02 05 01 55 0e 65 11 35 00 75 10 95 02 46 c8 0a 26 6f 08 09 30 81 02 35 00 35 00 46 18 06 26 77 0f 09 31 81 02 35 00 35 00 05 0d 95 01 75 08 15 00 26 ff 00 46 ff 00 09 48 81 02 09 49 81 02 c0 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 01 81 03 95 01 81 03 25 1f 75 05 09 51 81 02 05 01 55 0e 65 11 35 00 75 10 95 02 46 c8 0a 26 6f 08 09 30 81 02 35 00 35 00 46 18 06 26 77 0f 09 31 81 02 35 00 35 00 05 0d 95 01 75 08 15 00 26 ff 00 46 ff 00 09 48 81 02 09 49 81 02 c0 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 01 81 03 95 01 81 03 25 1f 75 05 09 51 81 02 05 01 55 0e 65 11 35 00 75 10 95 02 46 c8 0a 26 6f 08 09 30 81 02 35 00 35 00 46 18 06 26 77 0f 09 31 81 02 35 00 35 00 05 0d 95 01 75 08 15 00 26 ff 00 46 ff 00 09 48 81 02 09 49 81 02 c0 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 01 81 03 95 01 81 03 25 1f 75 05 09 51 81 02 05 01 55 0e 65 11 35 00 75 10 95 02 46 c8 0a 26 6f 08 09 30 81 02 35 00 35 00 46 18 06 26 77 0f 09 31 81 02 35 00 35 00 05 0d 95 01 75 08 15 00 26 ff 00 46 ff 00 09 48 81 02 09 49 81 02 c0 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 01 81 03 95 01 81 03 25 1f 75 05 09 51 81 02 05 01 55 0e 65 11 35 00 75 10 95 02 46 c8 0a 26 6f 08 09 30 81 02 35 00 35 00 46 18 06 26 77 0f 09 31 81 02 35 00 35 00 05 0d 95 01 75 08 15 00 26 ff 00 46 ff 00 09 48 81 02 09 49 81 02 c0 05 0d 27 ff ff 00 00 75 10 95 01 09 56 81 02 15 00 25 1f 75 05 09 54 95 01 81 02 75 03 25 01 95 01 81 03 75 08 85 02 09 55 25 10 b1 02 06 00 ff 85 05 09 c5 15 00 26 ff 00 75 08 96 00 01 b1 02 c0 05 0d 09 00 a1 01 85 03 09 20 a1 00 15 00 25 01 75 01 95 01 09 42 81 02 09 44 81 02 09 45 81 02 81 03 09 32 81 02 95 03 81 03 05 01 55 0e 65 11 35 00 75 10 95 02 46 c8 0a 26 6f 08 09 30 81 02 46 18 06 26 77 0f 09 31 81 02 05 0d 09 30 15 01 26 ff 00 75 08 95 01 81 02 c0 c0")


@unittest.skip('still WIP (Pen node)')
class Testatmel_03eb_840b(BaseTest.TestMultitouch):
    def _create_device(self):
        return Digitizer("uhid test atmel_03eb_840b", rdesc="639 05 0d 09 04 a1 01 85 01 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 01 81 03 95 01 81 03 25 1f 75 05 09 51 81 02 05 01 55 0e 65 11 35 00 75 10 95 01 46 00 0a 26 ff 0f 09 30 81 02 09 00 81 03 46 a0 05 26 ff 0f 09 31 81 02 09 00 81 03 05 0d 95 01 75 08 15 00 26 ff 00 46 ff 00 09 00 81 03 09 00 81 03 c0 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 01 81 03 95 01 81 03 25 1f 75 05 09 51 81 02 05 01 55 0e 65 11 35 00 75 10 95 01 46 00 0a 26 ff 0f 09 30 81 02 09 00 81 03 46 a0 05 26 ff 0f 09 31 81 02 09 00 81 03 05 0d 95 01 75 08 15 00 26 ff 00 46 ff 00 09 00 81 03 09 00 81 03 c0 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 01 81 03 95 01 81 03 25 1f 75 05 09 51 81 02 05 01 55 0e 65 11 35 00 75 10 95 01 46 00 0a 26 ff 0f 09 30 81 02 09 00 81 03 46 a0 05 26 ff 0f 09 31 81 02 09 00 81 03 05 0d 95 01 75 08 15 00 26 ff 00 46 ff 00 09 00 81 03 09 00 81 03 c0 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 01 81 03 95 01 81 03 25 1f 75 05 09 51 81 02 05 01 55 0e 65 11 35 00 75 10 95 01 46 00 0a 26 ff 0f 09 30 81 02 09 00 81 03 46 a0 05 26 ff 0f 09 31 81 02 09 00 81 03 05 0d 95 01 75 08 15 00 26 ff 00 46 ff 00 09 00 81 03 09 00 81 03 c0 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 01 81 03 95 01 81 03 25 1f 75 05 09 51 81 02 05 01 55 0e 65 11 35 00 75 10 95 01 46 00 0a 26 ff 0f 09 30 81 02 09 00 81 03 46 a0 05 26 ff 0f 09 31 81 02 09 00 81 03 05 0d 95 01 75 08 15 00 26 ff 00 46 ff 00 09 00 81 03 09 00 81 03 c0 05 0d 27 ff ff 00 00 75 10 95 01 09 56 81 02 15 00 25 1f 75 05 09 54 95 01 81 02 75 03 25 01 95 01 81 03 75 08 85 02 09 55 25 10 b1 02 06 00 ff 85 05 09 c5 15 00 26 ff 00 75 08 96 00 01 b1 02 c0 05 0d 09 02 a1 01 85 03 09 20 a1 00 15 00 25 01 75 01 95 01 09 42 81 02 09 44 81 02 09 45 81 02 81 03 09 32 81 02 95 03 81 03 05 01 55 0e 65 11 35 00 75 10 95 02 46 00 0a 26 ff 0f 09 30 81 02 46 a0 05 26 ff 0f 09 31 81 02 05 0d 09 30 15 01 26 ff 00 75 08 95 01 81 02 c0 c0")


class Testegalax_capacitive_0eef_790a(BaseTest.TestMultitouch):
    def _create_device(self):
        return Digitizer("uhid test egalax_capacitive_0eef_790a", rdesc="557 05 0d 09 04 a1 01 85 06 05 0d 09 54 75 08 15 00 25 0c 95 01 81 02 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 07 81 03 75 08 09 51 95 01 15 00 25 20 81 02 05 01 26 ff 0f 75 10 55 0e 65 11 09 30 35 00 46 13 0c 81 02 46 cb 06 09 31 81 02 75 08 95 02 81 03 81 03 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 07 81 03 75 08 09 51 95 01 15 00 25 20 81 02 05 01 26 ff 0f 75 10 55 0e 65 11 09 30 35 00 46 13 0c 81 02 46 cb 06 09 31 81 02 75 08 95 02 81 03 81 03 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 07 81 03 75 08 09 51 95 01 15 00 25 20 81 02 05 01 26 ff 0f 75 10 55 0e 65 11 09 30 35 00 46 13 0c 81 02 46 cb 06 09 31 81 02 75 08 95 02 81 03 81 03 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 07 81 03 75 08 09 51 95 01 15 00 25 20 81 02 05 01 26 ff 0f 75 10 55 0e 65 11 09 30 35 00 46 13 0c 81 02 46 cb 06 09 31 81 02 75 08 95 02 81 03 81 03 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 07 81 03 75 08 09 51 95 01 15 00 25 20 81 02 05 01 26 ff 0f 75 10 55 0e 65 11 09 30 35 00 46 13 0c 81 02 46 cb 06 09 31 81 02 75 08 95 02 81 03 81 03 c0 05 0d 17 00 00 00 00 27 ff ff ff 7f 75 20 95 01 55 00 65 00 09 56 81 02 09 55 09 53 75 08 95 02 26 ff 00 b1 02 06 00 ff 09 c5 85 07 15 00 26 ff 00 75 08 96 00 01 b1 02 c0 05 01 09 01 a1 01 85 01 09 01 a1 02 05 09 19 01 29 02 15 00 25 01 95 02 75 01 81 02 95 01 75 06 81 01 05 01 09 30 09 31 16 00 00 26 ff 0f 36 00 00 46 ff 0f 66 00 00 75 10 95 02 81 02 c0 c0 06 00 ff 09 01 a1 01 09 01 15 00 26 ff 00 85 03 75 08 95 3f 81 02 06 00 ff 09 01 15 00 26 ff 00 75 08 95 3f 91 02 c0 05 0d 09 0e a1 01 85 05 09 23 a1 02 09 52 09 53 15 00 25 0a 75 08 95 02 b1 02 c0 c0")


class Testelan_04f3_000a(BaseTest.TestMultitouch):
    def _create_device(self):
        return Digitizer("uhid test elan_04f3_000a", rdesc="925 05 0d 09 04 a1 01 85 01 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 c0 0e 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 00 08 46 a6 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 c0 0e 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 00 08 46 a6 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 c0 0e 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 00 08 46 a6 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 c0 0e 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 00 08 46 a6 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 c0 0e 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 00 08 46 a6 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 c0 0e 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 00 08 46 a6 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 c0 0e 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 00 08 46 a6 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 c0 0e 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 00 08 46 a6 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 c0 0e 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 00 08 46 a6 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 c0 0e 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 00 08 46 a6 00 09 31 81 02 c0 05 0d 09 56 55 00 65 00 27 ff ff ff 7f 95 01 75 20 81 02 09 54 25 7f 95 01 75 08 81 02 85 0a 09 55 25 0a b1 02 85 44 06 00 ff 09 c5 15 00 26 ff 00 75 08 96 00 01 b1 02 c0 06 ff 01 09 01 a1 01 85 02 15 00 26 ff 00 75 08 95 40 09 00 81 02 c0 06 00 ff 09 01 a1 01 85 03 75 08 95 1f 09 01 91 02 c0 06 01 ff 09 01 a1 01 85 04 15 00 26 ff 00 75 08 95 13 09 00 81 02 c0")


class Testelan_04f3_000c(BaseTest.TestMultitouch):
    def _create_device(self):
        return Digitizer("uhid test elan_04f3_000c", rdesc="925 05 0d 09 04 a1 01 85 01 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 40 0e 75 10 55 0f 65 11 09 30 35 00 46 01 01 95 02 81 02 26 00 08 46 91 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 40 0e 75 10 55 0f 65 11 09 30 35 00 46 01 01 95 02 81 02 26 00 08 46 91 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 40 0e 75 10 55 0f 65 11 09 30 35 00 46 01 01 95 02 81 02 26 00 08 46 91 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 40 0e 75 10 55 0f 65 11 09 30 35 00 46 01 01 95 02 81 02 26 00 08 46 91 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 40 0e 75 10 55 0f 65 11 09 30 35 00 46 01 01 95 02 81 02 26 00 08 46 91 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 40 0e 75 10 55 0f 65 11 09 30 35 00 46 01 01 95 02 81 02 26 00 08 46 91 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 40 0e 75 10 55 0f 65 11 09 30 35 00 46 01 01 95 02 81 02 26 00 08 46 91 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 40 0e 75 10 55 0f 65 11 09 30 35 00 46 01 01 95 02 81 02 26 00 08 46 91 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 40 0e 75 10 55 0f 65 11 09 30 35 00 46 01 01 95 02 81 02 26 00 08 46 91 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 40 0e 75 10 55 0f 65 11 09 30 35 00 46 01 01 95 02 81 02 26 00 08 46 91 00 09 31 81 02 c0 05 0d 09 56 55 00 65 00 27 ff ff ff 7f 95 01 75 20 81 02 09 54 25 7f 95 01 75 08 81 02 85 0a 09 55 25 0a b1 02 85 44 06 00 ff 09 c5 15 00 26 ff 00 75 08 96 00 01 b1 02 c0 06 ff 01 09 01 a1 01 85 02 15 00 26 ff 00 75 08 95 40 09 00 81 02 c0 06 00 ff 09 01 a1 01 85 03 75 08 95 1f 09 01 91 02 c0 06 01 ff 09 01 a1 01 85 04 15 00 26 ff 00 75 08 95 13 09 00 81 02 c0")


class Testelan_04f3_010c(BaseTest.TestMultitouch):
    def _create_device(self):
        return Digitizer("uhid test elan_04f3_010c", rdesc="925 05 0d 09 04 a1 01 85 01 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 f0 0c 75 10 55 0f 65 11 09 30 35 00 46 58 01 95 02 81 02 26 50 07 46 c2 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 f0 0c 75 10 55 0f 65 11 09 30 35 00 46 58 01 95 02 81 02 26 50 07 46 c2 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 f0 0c 75 10 55 0f 65 11 09 30 35 00 46 58 01 95 02 81 02 26 50 07 46 c2 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 f0 0c 75 10 55 0f 65 11 09 30 35 00 46 58 01 95 02 81 02 26 50 07 46 c2 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 f0 0c 75 10 55 0f 65 11 09 30 35 00 46 58 01 95 02 81 02 26 50 07 46 c2 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 f0 0c 75 10 55 0f 65 11 09 30 35 00 46 58 01 95 02 81 02 26 50 07 46 c2 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 f0 0c 75 10 55 0f 65 11 09 30 35 00 46 58 01 95 02 81 02 26 50 07 46 c2 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 f0 0c 75 10 55 0f 65 11 09 30 35 00 46 58 01 95 02 81 02 26 50 07 46 c2 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 f0 0c 75 10 55 0f 65 11 09 30 35 00 46 58 01 95 02 81 02 26 50 07 46 c2 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 f0 0c 75 10 55 0f 65 11 09 30 35 00 46 58 01 95 02 81 02 26 50 07 46 c2 00 09 31 81 02 c0 05 0d 09 56 55 00 65 00 27 ff ff ff 7f 95 01 75 20 81 02 09 54 25 7f 95 01 75 08 81 02 85 0a 09 55 25 0a b1 02 85 44 06 00 ff 09 c5 15 00 26 ff 00 75 08 96 00 01 b1 02 c0 06 ff 01 09 01 a1 01 85 02 15 00 26 ff 00 75 08 95 40 09 00 81 02 c0 06 00 ff 09 01 a1 01 85 03 75 08 95 1f 09 01 91 02 c0 06 01 ff 09 01 a1 01 85 04 15 00 26 ff 00 75 08 95 13 09 00 81 02 c0")


class Testelan_04f3_0125(BaseTest.TestMultitouch):
    def _create_device(self):
        return Digitizer("uhid test elan_04f3_0125", rdesc="925 05 0d 09 04 a1 01 85 01 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 f0 0c 75 10 55 0f 65 11 09 30 35 00 46 58 01 95 02 81 02 26 50 07 46 c1 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 f0 0c 75 10 55 0f 65 11 09 30 35 00 46 58 01 95 02 81 02 26 50 07 46 c1 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 f0 0c 75 10 55 0f 65 11 09 30 35 00 46 58 01 95 02 81 02 26 50 07 46 c1 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 f0 0c 75 10 55 0f 65 11 09 30 35 00 46 58 01 95 02 81 02 26 50 07 46 c1 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 f0 0c 75 10 55 0f 65 11 09 30 35 00 46 58 01 95 02 81 02 26 50 07 46 c1 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 f0 0c 75 10 55 0f 65 11 09 30 35 00 46 58 01 95 02 81 02 26 50 07 46 c1 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 f0 0c 75 10 55 0f 65 11 09 30 35 00 46 58 01 95 02 81 02 26 50 07 46 c1 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 f0 0c 75 10 55 0f 65 11 09 30 35 00 46 58 01 95 02 81 02 26 50 07 46 c1 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 f0 0c 75 10 55 0f 65 11 09 30 35 00 46 58 01 95 02 81 02 26 50 07 46 c1 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 f0 0c 75 10 55 0f 65 11 09 30 35 00 46 58 01 95 02 81 02 26 50 07 46 c1 00 09 31 81 02 c0 05 0d 09 56 55 00 65 00 27 ff ff ff 7f 95 01 75 20 81 02 09 54 25 7f 95 01 75 08 81 02 85 0a 09 55 25 0a b1 02 85 44 06 00 ff 09 c5 15 00 26 ff 00 75 08 96 00 01 b1 02 c0 06 ff 01 09 01 a1 01 85 02 15 00 26 ff 00 75 08 95 40 09 00 81 02 c0 06 00 ff 09 01 a1 01 85 03 75 08 95 1f 09 01 91 02 c0 06 01 ff 09 01 a1 01 85 04 15 00 26 ff 00 75 08 95 13 09 00 81 02 c0")


class Testelan_04f3_016f(BaseTest.TestMultitouch):
    def _create_device(self):
        return Digitizer("uhid test elan_04f3_016f", rdesc="925 05 0d 09 04 a1 01 85 01 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 c0 0e 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 40 08 46 a6 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 c0 0e 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 40 08 46 a6 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 c0 0e 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 40 08 46 a6 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 c0 0e 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 40 08 46 a6 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 c0 0e 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 40 08 46 a6 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 c0 0e 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 40 08 46 a6 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 c0 0e 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 40 08 46 a6 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 c0 0e 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 40 08 46 a6 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 c0 0e 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 40 08 46 a6 00 09 31 81 02 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 c0 0e 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 40 08 46 a6 00 09 31 81 02 c0 05 0d 09 56 55 00 65 00 27 ff ff ff 7f 95 01 75 20 81 02 09 54 25 7f 95 01 75 08 81 02 85 0a 09 55 25 0a b1 02 85 44 06 00 ff 09 c5 15 00 26 ff 00 75 08 96 00 01 b1 02 c0 06 ff 01 09 01 a1 01 85 02 15 00 26 ff 00 75 08 95 40 09 00 81 02 c0 06 00 ff 09 01 a1 01 85 03 75 08 95 1f 09 01 91 02 c0 06 01 ff 09 01 a1 01 85 04 15 00 26 ff 00 75 08 95 13 09 00 81 02 c0")


@unittest.skip('still WIP (PTP)')
class Testelan_04f3_0732(BaseTest.TestMultitouch):
    def _create_device(self):
        return Digitizer("uhid test elan_04f3_0732", rdesc="883 05 0d 09 04 a1 01 85 01 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 09 32 81 02 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 c0 0b 75 10 55 0f 65 11 09 30 35 00 46 ff 00 95 02 81 02 26 40 07 46 85 00 09 31 81 02 c0 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 09 32 81 02 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 c0 0b 75 10 55 0f 65 11 09 30 35 00 46 ff 00 95 02 81 02 26 40 07 46 85 00 09 31 81 02 c0 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 09 32 81 02 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 c0 0b 75 10 55 0f 65 11 09 30 35 00 46 ff 00 95 02 81 02 26 40 07 46 85 00 09 31 81 02 c0 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 09 32 81 02 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 c0 0b 75 10 55 0f 65 11 09 30 35 00 46 ff 00 95 02 81 02 26 40 07 46 85 00 09 31 81 02 c0 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 09 32 81 02 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 c0 0b 75 10 55 0f 65 11 09 30 35 00 46 ff 00 95 02 81 02 26 40 07 46 85 00 09 31 81 02 c0 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 09 32 81 02 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 c0 0b 75 10 55 0f 65 11 09 30 35 00 46 ff 00 95 02 81 02 26 40 07 46 85 00 09 31 81 02 c0 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 09 32 81 02 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 c0 0b 75 10 55 0f 65 11 09 30 35 00 46 ff 00 95 02 81 02 26 40 07 46 85 00 09 31 81 02 c0 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 09 32 81 02 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 c0 0b 75 10 55 0f 65 11 09 30 35 00 46 ff 00 95 02 81 02 26 40 07 46 85 00 09 31 81 02 c0 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 09 32 81 02 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 c0 0b 75 10 55 0f 65 11 09 30 35 00 46 ff 00 95 02 81 02 26 40 07 46 85 00 09 31 81 02 c0 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 09 32 81 02 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 c0 0b 75 10 55 0f 65 11 09 30 35 00 46 ff 00 95 02 81 02 26 40 07 46 85 00 09 31 81 02 c0 05 0d 09 56 55 00 65 00 27 ff ff 00 00 95 01 75 20 81 02 09 54 25 7f 95 01 75 08 81 02 85 0a 09 55 25 0a b1 02 85 44 06 00 ff 09 c5 15 00 26 ff 00 75 08 96 00 01 b1 02 c0 06 ff 01 09 01 a1 01 85 02 15 00 25 ff 75 08 95 40 09 00 81 02 c0 06 00 ff 09 01 a1 01 85 03 75 08 95 1f 09 01 91 02 c0")


@unittest.skip('still WIP (PTP)')
class Testelan_04f3_200a(BaseTest.TestMultitouch):
    def _create_device(self):
        return Digitizer("uhid test elan_04f3_200a", rdesc="219 05 0d 09 04 a1 01 85 01 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 09 32 81 02 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 c0 0e 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 40 08 46 a6 00 09 31 81 02 c0 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 09 32 81 02 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 26 c0 0e 75 10 55 0f 65 11 09 30 35 00 46 26 01 95 02 81 02 26 40 08 46 a6 00 09 31 81 02 c0 05 0d 09 56 55 00 65 00 27 ff ff 00 00 95 01 75 20 81 02 09 54 25 7f 95 01 75 08 81 02 85 0a 09 55 25 0a b1 02 85 0e 06 00 ff 09 c5 15 00 26 ff 00 75 08 96 00 01 b1 02 c0")


@unittest.skip('still WIP (PTP)')
class Testelan_04f3_300b(BaseTest.TestMultitouch):
    def _create_device(self):
        return Digitizer("uhid test elan_04f3_300b", rdesc="361 05 01 09 02 a1 01 85 01 09 01 a1 00 05 09 19 01 29 02 15 00 25 01 75 01 95 02 81 02 95 06 81 03 05 01 09 30 09 31 09 38 15 81 25 7f 75 08 95 03 81 06 05 0c 0a 38 02 95 01 81 06 75 08 95 03 81 03 c0 06 00 ff 85 0d 09 c5 15 00 26 ff 00 75 08 95 04 b1 02 85 0c 09 c6 96 76 02 75 08 b1 02 85 0b 09 c7 95 42 75 08 b1 02 09 01 85 5d 95 1f 75 08 81 06 c0 05 0d 09 05 a1 01 85 04 09 22 a1 02 15 00 25 01 09 47 09 42 95 02 75 01 81 02 95 01 75 02 25 02 09 51 81 02 75 01 95 04 81 03 05 01 15 00 26 a7 0c 75 10 55 0e 65 13 09 30 35 00 46 9d 01 95 01 81 02 46 25 01 26 2b 09 26 2b 09 09 31 81 02 05 0d 15 00 25 64 95 03 c0 55 0c 66 01 10 47 ff ff 00 00 27 ff ff 00 00 75 10 95 01 09 56 81 02 09 54 25 7f 95 01 75 08 81 02 05 09 09 01 25 01 75 01 95 01 81 02 95 07 81 03 05 0d 85 02 09 55 09 59 75 04 95 02 25 0f b1 02 85 07 09 60 75 01 95 01 15 00 25 01 b1 02 95 0f b1 03 06 00 ff 06 00 ff 85 06 09 c5 15 00 26 ff 00 75 08 96 00 01 b1 02 c0 05 0d 09 0e a1 01 85 03 09 22 a1 00 09 52 15 00 25 0a 75 08 95 02 b1 02 c0 09 22 a1 00 85 05 09 57 09 58 15 00 75 01 95 02 25 03 b1 02 95 0e b1 03 c0 c0")


class Testilitek_222a_0015(BaseTest.TestMultitouch):
    def _create_device(self):
        return Digitizer("uhid test ilitek_222a_0015", rdesc="772 05 0d 09 04 a1 01 85 04 09 22 a1 02 05 0d 95 01 75 06 09 51 15 00 25 3f 81 02 09 42 25 01 75 01 95 01 81 02 75 01 95 01 81 03 05 01 75 10 55 0e 65 11 09 30 26 c2 16 35 00 46 b3 08 81 42 09 31 26 c2 0c 46 e4 04 81 42 c0 05 0d 09 22 a1 02 05 0d 95 01 75 06 09 51 15 00 25 3f 81 02 09 42 25 01 75 01 95 01 81 02 75 01 95 01 81 03 05 01 75 10 55 0e 65 11 09 30 26 c2 16 35 00 46 b3 08 81 42 09 31 26 c2 0c 46 e4 04 81 42 c0 05 0d 09 22 a1 02 05 0d 95 01 75 06 09 51 15 00 25 3f 81 02 09 42 25 01 75 01 95 01 81 02 75 01 95 01 81 03 05 01 75 10 55 0e 65 11 09 30 26 c2 16 35 00 46 b3 08 81 42 09 31 26 c2 0c 46 e4 04 81 42 c0 05 0d 09 22 a1 02 05 0d 95 01 75 06 09 51 15 00 25 3f 81 02 09 42 25 01 75 01 95 01 81 02 75 01 95 01 81 03 05 01 75 10 55 0e 65 11 09 30 26 c2 16 35 00 46 b3 08 81 42 09 31 26 c2 0c 46 e4 04 81 42 c0 05 0d 09 22 a1 02 05 0d 95 01 75 06 09 51 15 00 25 3f 81 02 09 42 25 01 75 01 95 01 81 02 75 01 95 01 81 03 05 01 75 10 55 0e 65 11 09 30 26 c2 16 35 00 46 b3 08 81 42 09 31 26 c2 0c 46 e4 04 81 42 c0 05 0d 09 22 a1 02 05 0d 95 01 75 06 09 51 15 00 25 3f 81 02 09 42 25 01 75 01 95 01 81 02 75 01 95 01 81 03 05 01 75 10 55 0e 65 11 09 30 26 c2 16 35 00 46 b3 08 81 42 09 31 26 c2 0c 46 e4 04 81 42 c0 05 0d 09 22 a1 02 05 0d 95 01 75 06 09 51 15 00 25 3f 81 02 09 42 25 01 75 01 95 01 81 02 75 01 95 01 81 03 05 01 75 10 55 0e 65 11 09 30 26 c2 16 35 00 46 b3 08 81 42 09 31 26 c2 0c 46 e4 04 81 42 c0 05 0d 09 22 a1 02 05 0d 95 01 75 06 09 51 15 00 25 3f 81 02 09 42 25 01 75 01 95 01 81 02 75 01 95 01 81 03 05 01 75 10 55 0e 65 11 09 30 26 c2 16 35 00 46 b3 08 81 42 09 31 26 c2 0c 46 e4 04 81 42 c0 05 0d 09 22 a1 02 05 0d 95 01 75 06 09 51 15 00 25 3f 81 02 09 42 25 01 75 01 95 01 81 02 75 01 95 01 81 03 05 01 75 10 55 0e 65 11 09 30 26 c2 16 35 00 46 b3 08 81 42 09 31 26 c2 0c 46 e4 04 81 42 c0 05 0d 09 22 a1 02 05 0d 95 01 75 06 09 51 15 00 25 3f 81 02 09 42 25 01 75 01 95 01 81 02 75 01 95 01 81 03 05 01 75 10 55 0e 65 11 09 30 26 c2 16 35 00 46 b3 08 81 42 09 31 26 c2 0c 46 e4 04 81 42 c0 05 0d 09 56 55 00 65 00 27 ff ff ff 7f 95 01 75 20 81 02 09 54 25 7f 95 01 75 08 81 02 85 02 09 55 25 0a b1 02 06 00 ff 09 c5 85 06 15 00 26 ff 00 75 08 96 00 01 b1 02 c0 06 00 ff 09 01 a1 01 09 01 85 03 15 00 26 ff 00 75 08 95 3f 81 02 06 00 ff 09 01 15 00 26 ff 00 75 08 95 3f 91 02 c0")


class Testilitek_222a_001c(BaseTest.TestMultitouch):
    def _create_device(self):
        return Digitizer("uhid test ilitek_222a_001c", rdesc="772 05 0d 09 04 a1 01 85 04 09 22 a1 02 05 0d 95 01 75 06 09 51 15 00 25 3f 81 02 09 42 25 01 75 01 95 01 81 02 75 01 95 01 81 03 05 01 75 10 55 0e 65 11 09 30 26 74 1d 35 00 46 70 0d 81 42 09 31 26 74 10 46 8f 07 81 42 c0 05 0d 09 22 a1 02 05 0d 95 01 75 06 09 51 15 00 25 3f 81 02 09 42 25 01 75 01 95 01 81 02 75 01 95 01 81 03 05 01 75 10 55 0e 65 11 09 30 26 74 1d 35 00 46 70 0d 81 42 09 31 26 74 10 46 8f 07 81 42 c0 05 0d 09 22 a1 02 05 0d 95 01 75 06 09 51 15 00 25 3f 81 02 09 42 25 01 75 01 95 01 81 02 75 01 95 01 81 03 05 01 75 10 55 0e 65 11 09 30 26 74 1d 35 00 46 70 0d 81 42 09 31 26 74 10 46 8f 07 81 42 c0 05 0d 09 22 a1 02 05 0d 95 01 75 06 09 51 15 00 25 3f 81 02 09 42 25 01 75 01 95 01 81 02 75 01 95 01 81 03 05 01 75 10 55 0e 65 11 09 30 26 74 1d 35 00 46 70 0d 81 42 09 31 26 74 10 46 8f 07 81 42 c0 05 0d 09 22 a1 02 05 0d 95 01 75 06 09 51 15 00 25 3f 81 02 09 42 25 01 75 01 95 01 81 02 75 01 95 01 81 03 05 01 75 10 55 0e 65 11 09 30 26 74 1d 35 00 46 70 0d 81 42 09 31 26 74 10 46 8f 07 81 42 c0 05 0d 09 22 a1 02 05 0d 95 01 75 06 09 51 15 00 25 3f 81 02 09 42 25 01 75 01 95 01 81 02 75 01 95 01 81 03 05 01 75 10 55 0e 65 11 09 30 26 74 1d 35 00 46 70 0d 81 42 09 31 26 74 10 46 8f 07 81 42 c0 05 0d 09 22 a1 02 05 0d 95 01 75 06 09 51 15 00 25 3f 81 02 09 42 25 01 75 01 95 01 81 02 75 01 95 01 81 03 05 01 75 10 55 0e 65 11 09 30 26 74 1d 35 00 46 70 0d 81 42 09 31 26 74 10 46 8f 07 81 42 c0 05 0d 09 22 a1 02 05 0d 95 01 75 06 09 51 15 00 25 3f 81 02 09 42 25 01 75 01 95 01 81 02 75 01 95 01 81 03 05 01 75 10 55 0e 65 11 09 30 26 74 1d 35 00 46 70 0d 81 42 09 31 26 74 10 46 8f 07 81 42 c0 05 0d 09 22 a1 02 05 0d 95 01 75 06 09 51 15 00 25 3f 81 02 09 42 25 01 75 01 95 01 81 02 75 01 95 01 81 03 05 01 75 10 55 0e 65 11 09 30 26 74 1d 35 00 46 70 0d 81 42 09 31 26 74 10 46 8f 07 81 42 c0 05 0d 09 22 a1 02 05 0d 95 01 75 06 09 51 15 00 25 3f 81 02 09 42 25 01 75 01 95 01 81 02 75 01 95 01 81 03 05 01 75 10 55 0e 65 11 09 30 26 74 1d 35 00 46 70 0d 81 42 09 31 26 74 10 46 8f 07 81 42 c0 05 0d 09 56 55 00 65 00 27 ff ff ff 7f 95 01 75 20 81 02 09 54 25 7f 95 01 75 08 81 02 85 02 09 55 25 0a b1 02 06 00 ff 09 c5 85 06 15 00 26 ff 00 75 08 96 00 01 b1 02 c0 06 00 ff 09 01 a1 01 09 01 85 03 15 00 26 ff 00 75 08 95 3f 81 02 06 00 ff 09 01 15 00 26 ff 00 75 08 95 3f 91 02 c0")


@unittest.skip('still WIP')
class Testn_trig_1b96_0c01(BaseTest.TestMultitouch):
    def _create_device(self):
        return Digitizer("uhid test n_trig_1b96_0c01", rdesc="1492 75 08 15 00 26 ff 00 06 0b ff 09 0b a1 01 95 0f 09 29 85 29 b1 02 95 1f 09 2a 85 2a b1 02 95 3e 09 2b 85 2b b1 02 95 fe 09 2c 85 2c b1 02 96 fe 01 09 2d 85 2d b1 02 95 02 09 48 85 48 b1 02 95 0f 09 2e 85 2e 81 02 95 1f 09 2f 85 2f 81 02 95 3e 09 30 85 30 81 02 95 fe 09 31 85 31 81 02 96 fe 01 09 32 85 32 81 02 75 08 96 fe 0f 09 35 85 35 81 02 c0 05 0d 09 02 a1 01 85 01 09 20 35 00 a1 00 09 32 09 42 09 44 09 3c 09 45 15 00 25 01 75 01 95 05 81 02 95 03 81 03 05 01 09 30 75 10 95 01 a4 55 0e 65 11 46 15 0a 26 80 25 81 02 09 31 46 b4 05 26 20 1c 81 02 b4 05 0d 09 30 26 00 01 81 02 06 00 ff 09 01 81 02 c0 85 0c 06 00 ff 09 0c 75 08 95 06 26 ff 00 b1 02 85 0b 09 0b 95 02 b1 02 85 11 09 11 b1 02 85 15 09 15 95 05 b1 02 85 18 09 18 95 0c b1 02 c0 05 0d 09 04 a1 01 85 03 06 00 ff 09 01 75 10 95 01 15 00 27 ff ff 00 00 81 02 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 09 32 81 02 09 47 81 02 95 05 81 03 75 10 09 51 27 ff ff 00 00 95 01 81 02 05 01 09 30 75 10 95 02 a4 55 0e 65 11 46 15 0a 26 80 25 81 02 09 31 46 b4 05 26 20 1c 81 02 05 0d 09 48 95 01 26 80 25 81 02 09 49 26 20 1c 81 02 b4 06 00 ff 09 02 75 08 95 04 15 00 26 ff 00 81 02 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 09 32 81 02 09 47 81 02 95 05 81 03 75 10 09 51 27 ff ff 00 00 95 01 81 02 05 01 09 30 75 10 95 02 a4 55 0e 65 11 46 15 0a 26 80 25 81 02 09 31 46 b4 05 26 20 1c 81 02 05 0d 09 48 95 01 26 80 25 81 02 09 49 26 20 1c 81 02 b4 06 00 ff 09 02 75 08 95 04 15 00 26 ff 00 81 02 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 09 32 81 02 09 47 81 02 95 05 81 03 75 10 09 51 27 ff ff 00 00 95 01 81 02 05 01 09 30 75 10 95 02 a4 55 0e 65 11 46 15 0a 26 80 25 81 02 09 31 46 b4 05 26 20 1c 81 02 05 0d 09 48 95 01 26 80 25 81 02 09 49 26 20 1c 81 02 b4 06 00 ff 09 02 75 08 95 04 15 00 26 ff 00 81 02 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 09 32 81 02 09 47 81 02 95 05 81 03 75 10 09 51 27 ff ff 00 00 95 01 81 02 05 01 09 30 75 10 95 02 a4 55 0e 65 11 46 15 0a 26 80 25 81 02 09 31 46 b4 05 26 20 1c 81 02 05 0d 09 48 95 01 26 80 25 81 02 09 49 26 20 1c 81 02 b4 06 00 ff 09 02 75 08 95 04 15 00 26 ff 00 81 02 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 09 32 81 02 09 47 81 02 95 05 81 03 75 10 09 51 27 ff ff 00 00 95 01 81 02 05 01 09 30 75 10 95 02 a4 55 0e 65 11 46 15 0a 26 80 25 81 02 09 31 46 b4 05 26 20 1c 81 02 05 0d 09 48 95 01 26 80 25 81 02 09 49 26 20 1c 81 02 b4 06 00 ff 09 02 75 08 95 04 15 00 26 ff 00 81 02 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 09 32 81 02 09 47 81 02 95 05 81 03 75 10 09 51 27 ff ff 00 00 95 01 81 02 05 01 09 30 75 10 95 02 a4 55 0e 65 11 46 15 0a 26 80 25 81 02 09 31 46 b4 05 26 20 1c 81 02 05 0d 09 48 95 01 26 80 25 81 02 09 49 26 20 1c 81 02 b4 06 00 ff 09 02 75 08 95 04 15 00 26 ff 00 81 02 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 09 32 81 02 09 47 81 02 95 05 81 03 75 10 09 51 27 ff ff 00 00 95 01 81 02 05 01 09 30 75 10 95 02 a4 55 0e 65 11 46 15 0a 26 80 25 81 02 09 31 46 b4 05 26 20 1c 81 02 05 0d 09 48 95 01 26 80 25 81 02 09 49 26 20 1c 81 02 b4 06 00 ff 09 02 75 08 95 04 15 00 26 ff 00 81 02 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 09 32 81 02 09 47 81 02 95 05 81 03 75 10 09 51 27 ff ff 00 00 95 01 81 02 05 01 09 30 75 10 95 02 a4 55 0e 65 11 46 15 0a 26 80 25 81 02 09 31 46 b4 05 26 20 1c 81 02 05 0d 09 48 95 01 26 80 25 81 02 09 49 26 20 1c 81 02 b4 06 00 ff 09 02 75 08 95 04 15 00 26 ff 00 81 02 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 09 32 81 02 09 47 81 02 95 05 81 03 75 10 09 51 27 ff ff 00 00 95 01 81 02 05 01 09 30 75 10 95 02 a4 55 0e 65 11 46 15 0a 26 80 25 81 02 09 31 46 b4 05 26 20 1c 81 02 05 0d 09 48 95 01 26 80 25 81 02 09 49 26 20 1c 81 02 b4 06 00 ff 09 02 75 08 95 04 15 00 26 ff 00 81 02 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 09 32 81 02 09 47 81 02 95 05 81 03 75 10 09 51 27 ff ff 00 00 95 01 81 02 05 01 09 30 75 10 95 02 a4 55 0e 65 11 46 15 0a 26 80 25 81 02 09 31 46 b4 05 26 20 1c 81 02 05 0d 09 48 95 01 26 80 25 81 02 09 49 26 20 1c 81 02 b4 06 00 ff 09 02 75 08 95 04 15 00 26 ff 00 81 02 c0 05 0d 09 54 95 01 75 08 81 02 09 56 75 20 95 01 27 ff ff ff 0f 81 02 85 04 09 55 75 08 95 01 25 0b b1 02 85 0a 06 00 ff 09 03 15 00 b1 02 85 1b 06 00 ff 09 c5 15 00 26 ff 00 75 08 96 00 01 b1 02 c0 05 01 09 02 a1 01 85 02 09 01 a1 00 05 09 19 01 29 02 15 00 25 01 75 01 95 02 81 02 95 06 81 03 05 01 09 30 09 31 15 81 25 7f 75 08 95 02 81 06 c0 c0")


@unittest.skip('still WIP')
class Testn_trig_1b96_0c03(BaseTest.TestMultitouch):
    def _create_device(self):
        return Digitizer("uhid test n_trig_1b96_0c03", rdesc="612 75 08 15 00 26 ff 00 06 0b ff 09 0b a1 01 95 0f 09 29 85 29 b1 02 95 1f 09 2a 85 2a b1 02 95 3e 09 2b 85 2b b1 02 95 fe 09 2c 85 2c b1 02 96 fe 01 09 2d 85 2d b1 02 95 02 09 48 85 48 b1 02 95 0f 09 2e 85 2e 81 02 95 1f 09 2f 85 2f 81 02 95 3e 09 30 85 30 81 02 95 fe 09 31 85 31 81 02 96 fe 01 09 32 85 32 81 02 75 08 96 fe 0f 09 35 85 35 81 02 c0 05 0d 09 02 a1 01 85 01 09 20 35 00 a1 00 09 32 09 42 09 44 09 3c 09 45 15 00 25 01 75 01 95 05 81 02 95 03 81 03 05 01 09 30 75 10 95 01 a4 55 0e 65 11 46 15 0a 26 80 25 81 02 09 31 46 b4 05 26 20 1c 81 02 b4 05 0d 09 30 26 00 01 81 02 06 00 ff 09 01 81 02 c0 85 0c 06 00 ff 09 0c 75 08 95 06 26 ff 00 b1 02 85 0b 09 0b 95 02 b1 02 85 11 09 11 b1 02 85 15 09 15 95 05 b1 02 85 18 09 18 95 0c b1 02 c0 05 0d 09 04 a1 01 85 03 06 00 ff 09 01 75 10 95 01 15 00 27 ff ff 00 00 81 02 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 01 81 03 09 47 81 02 95 05 81 03 75 10 09 51 27 ff ff 00 00 95 01 81 02 05 01 09 30 75 10 95 02 a4 55 0e 65 11 46 15 0a 26 80 25 81 02 09 31 46 b4 05 26 20 1c 81 02 05 0d 09 48 95 01 26 80 25 81 02 09 49 26 20 1c 81 02 b4 06 00 ff 09 02 75 08 95 04 15 00 26 ff 00 81 02 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 01 81 03 09 47 81 02 95 05 81 03 75 10 09 51 27 ff ff 00 00 95 01 81 02 05 01 09 30 75 10 95 02 a4 55 0e 65 11 46 15 0a 26 80 25 81 02 09 31 46 b4 05 26 20 1c 81 02 05 0d 09 48 95 01 26 80 25 81 02 09 49 26 20 1c 81 02 b4 06 00 ff 09 02 75 08 95 04 15 00 26 ff 00 81 02 c0 05 0d 09 54 95 01 75 08 81 02 09 56 75 20 95 01 27 ff ff ff 0f 81 02 85 04 09 55 75 08 95 01 25 0b b1 02 85 0a 06 00 ff 09 03 15 00 b1 02 85 1b 06 00 ff 09 c5 15 00 26 ff 00 75 08 96 00 01 b1 02 c0 05 01 09 02 a1 01 85 02 09 01 a1 00 05 09 19 01 29 02 15 00 25 01 75 01 95 02 81 02 95 06 81 03 05 01 09 30 09 31 15 81 25 7f 75 08 95 02 81 06 c0 c0")


@unittest.skip('still WIP')
class Testn_trig_1b96_0f00(BaseTest.TestMultitouch):
    def _create_device(self):
        return Digitizer("uhid test n_trig_1b96_0f00", rdesc="612 75 08 15 00 26 ff 00 06 0b ff 09 0b a1 01 95 0f 09 29 85 29 b1 02 95 1f 09 2a 85 2a b1 02 95 3e 09 2b 85 2b b1 02 95 fe 09 2c 85 2c b1 02 96 fe 01 09 2d 85 2d b1 02 95 02 09 48 85 48 b1 02 95 0f 09 2e 85 2e 81 02 95 1f 09 2f 85 2f 81 02 95 3e 09 30 85 30 81 02 95 fe 09 31 85 31 81 02 96 fe 01 09 32 85 32 81 02 75 08 96 fe 0f 09 35 85 35 81 02 c0 05 0d 09 02 a1 01 85 01 09 20 35 00 a1 00 09 32 09 42 09 44 09 3c 09 45 15 00 25 01 75 01 95 05 81 02 95 03 81 03 05 01 09 30 75 10 95 01 a4 55 0e 65 11 46 03 0a 26 80 25 81 02 09 31 46 a1 05 26 20 1c 81 02 b4 05 0d 09 30 26 00 01 81 02 06 00 ff 09 01 81 02 c0 85 0c 06 00 ff 09 0c 75 08 95 06 26 ff 00 b1 02 85 0b 09 0b 95 02 b1 02 85 11 09 11 b1 02 85 15 09 15 95 05 b1 02 85 18 09 18 95 0c b1 02 c0 05 0d 09 04 a1 01 85 03 06 00 ff 09 01 75 10 95 01 15 00 27 ff ff 00 00 81 02 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 01 81 03 09 47 81 02 95 05 81 03 75 10 09 51 27 ff ff 00 00 95 01 81 02 05 01 09 30 75 10 95 02 a4 55 0e 65 11 46 03 0a 26 80 25 81 02 09 31 46 a1 05 26 20 1c 81 02 05 0d 09 48 95 01 26 80 25 81 02 09 49 26 20 1c 81 02 b4 06 00 ff 09 02 75 08 95 04 15 00 26 ff 00 81 02 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 01 81 03 09 47 81 02 95 05 81 03 75 10 09 51 27 ff ff 00 00 95 01 81 02 05 01 09 30 75 10 95 02 a4 55 0e 65 11 46 03 0a 26 80 25 81 02 09 31 46 a1 05 26 20 1c 81 02 05 0d 09 48 95 01 26 80 25 81 02 09 49 26 20 1c 81 02 b4 06 00 ff 09 02 75 08 95 04 15 00 26 ff 00 81 02 c0 05 0d 09 54 95 01 75 08 81 02 09 56 75 20 95 01 27 ff ff ff 0f 81 02 85 04 09 55 75 08 95 01 25 0b b1 02 85 0a 06 00 ff 09 03 15 00 b1 02 85 1b 06 00 ff 09 c5 15 00 26 ff 00 75 08 96 00 01 b1 02 c0 05 01 09 02 a1 01 85 02 09 01 a1 00 05 09 19 01 29 02 15 00 25 01 75 01 95 02 81 02 95 06 81 03 05 01 09 30 09 31 15 81 25 7f 75 08 95 02 81 06 c0 c0")


@unittest.skip('still WIP')
class Testn_trig_1b96_0f04(BaseTest.TestMultitouch):
    def _create_device(self):
        return Digitizer("uhid test n_trig_1b96_0f04", rdesc="612 75 08 15 00 26 ff 00 06 0b ff 09 0b a1 01 95 0f 09 29 85 29 b1 02 95 1f 09 2a 85 2a b1 02 95 3e 09 2b 85 2b b1 02 95 fe 09 2c 85 2c b1 02 96 fe 01 09 2d 85 2d b1 02 95 02 09 48 85 48 b1 02 95 0f 09 2e 85 2e 81 02 95 1f 09 2f 85 2f 81 02 95 3e 09 30 85 30 81 02 95 fe 09 31 85 31 81 02 96 fe 01 09 32 85 32 81 02 75 08 96 fe 0f 09 35 85 35 81 02 c0 05 0d 09 02 a1 01 85 01 09 20 35 00 a1 00 09 32 09 42 09 44 09 3c 09 45 15 00 25 01 75 01 95 05 81 02 95 03 81 03 05 01 09 30 75 10 95 01 a4 55 0e 65 11 46 7f 0b 26 80 25 81 02 09 31 46 78 06 26 20 1c 81 02 b4 05 0d 09 30 26 00 01 81 02 06 00 ff 09 01 81 02 c0 85 0c 06 00 ff 09 0c 75 08 95 06 26 ff 00 b1 02 85 0b 09 0b 95 02 b1 02 85 11 09 11 b1 02 85 15 09 15 95 05 b1 02 85 18 09 18 95 0c b1 02 c0 05 0d 09 04 a1 01 85 03 06 00 ff 09 01 75 10 95 01 15 00 27 ff ff 00 00 81 02 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 01 81 03 09 47 81 02 95 05 81 03 75 10 09 51 27 ff ff 00 00 95 01 81 02 05 01 09 30 75 10 95 02 a4 55 0e 65 11 46 7f 0b 26 80 25 81 02 09 31 46 78 06 26 20 1c 81 02 05 0d 09 48 95 01 26 80 25 81 02 09 49 26 20 1c 81 02 b4 06 00 ff 09 02 75 08 95 04 15 00 26 ff 00 81 02 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 01 81 03 09 47 81 02 95 05 81 03 75 10 09 51 27 ff ff 00 00 95 01 81 02 05 01 09 30 75 10 95 02 a4 55 0e 65 11 46 7f 0b 26 80 25 81 02 09 31 46 78 06 26 20 1c 81 02 05 0d 09 48 95 01 26 80 25 81 02 09 49 26 20 1c 81 02 b4 06 00 ff 09 02 75 08 95 04 15 00 26 ff 00 81 02 c0 05 0d 09 54 95 01 75 08 81 02 09 56 75 20 95 01 27 ff ff ff 0f 81 02 85 04 09 55 75 08 95 01 25 0b b1 02 85 0a 06 00 ff 09 03 15 00 b1 02 85 1b 06 00 ff 09 c5 15 00 26 ff 00 75 08 96 00 01 b1 02 c0 05 01 09 02 a1 01 85 02 09 01 a1 00 05 09 19 01 29 02 15 00 25 01 75 01 95 02 81 02 95 06 81 03 05 01 09 30 09 31 15 81 25 7f 75 08 95 02 81 06 c0 c0")


@unittest.skip('still WIP')
class Testn_trig_1b96_1000(BaseTest.TestMultitouch):
    def _create_device(self):
        return Digitizer("uhid test n_trig_1b96_1000", rdesc="612 75 08 15 00 26 ff 00 06 0b ff 09 0b a1 01 95 0f 09 29 85 29 b1 02 95 1f 09 2a 85 2a b1 02 95 3e 09 2b 85 2b b1 02 95 fe 09 2c 85 2c b1 02 96 fe 01 09 2d 85 2d b1 02 95 02 09 48 85 48 b1 02 95 0f 09 2e 85 2e 81 02 95 1f 09 2f 85 2f 81 02 95 3e 09 30 85 30 81 02 95 fe 09 31 85 31 81 02 96 fe 01 09 32 85 32 81 02 75 08 96 fe 0f 09 35 85 35 81 02 c0 05 0d 09 02 a1 01 85 01 09 20 35 00 a1 00 09 32 09 42 09 44 09 3c 09 45 15 00 25 01 75 01 95 05 81 02 95 03 81 03 05 01 09 30 75 10 95 01 a4 55 0e 65 11 46 03 0a 26 80 25 81 02 09 31 46 a1 05 26 20 1c 81 02 b4 05 0d 09 30 26 00 01 81 02 06 00 ff 09 01 81 02 c0 85 0c 06 00 ff 09 0c 75 08 95 06 26 ff 00 b1 02 85 0b 09 0b 95 02 b1 02 85 11 09 11 b1 02 85 15 09 15 95 05 b1 02 85 18 09 18 95 0c b1 02 c0 05 0d 09 04 a1 01 85 03 06 00 ff 09 01 75 10 95 01 15 00 27 ff ff 00 00 81 02 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 01 81 03 09 47 81 02 95 05 81 03 75 10 09 51 27 ff ff 00 00 95 01 81 02 05 01 09 30 75 10 95 02 a4 55 0e 65 11 46 03 0a 26 80 25 81 02 09 31 46 a1 05 26 20 1c 81 02 05 0d 09 48 95 01 26 80 25 81 02 09 49 26 20 1c 81 02 b4 06 00 ff 09 02 75 08 95 04 15 00 26 ff 00 81 02 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 01 81 03 09 47 81 02 95 05 81 03 75 10 09 51 27 ff ff 00 00 95 01 81 02 05 01 09 30 75 10 95 02 a4 55 0e 65 11 46 03 0a 26 80 25 81 02 09 31 46 a1 05 26 20 1c 81 02 05 0d 09 48 95 01 26 80 25 81 02 09 49 26 20 1c 81 02 b4 06 00 ff 09 02 75 08 95 04 15 00 26 ff 00 81 02 c0 05 0d 09 54 95 01 75 08 81 02 09 56 75 20 95 01 27 ff ff ff 0f 81 02 85 04 09 55 75 08 95 01 25 0b b1 02 85 0a 06 00 ff 09 03 15 00 b1 02 85 1b 06 00 ff 09 c5 15 00 26 ff 00 75 08 96 00 01 b1 02 c0 05 01 09 02 a1 01 85 02 09 01 a1 00 05 09 19 01 29 02 15 00 25 01 75 01 95 02 81 02 95 06 81 03 05 01 09 30 09 31 15 81 25 7f 75 08 95 02 81 06 c0 c0")


class Testsharp_04dd_9681(BaseTest.TestMultitouch):
    def _create_device(self):
        return Digitizer("uhid test sharp_04dd_9681", rdesc="576 06 00 ff 09 01 a1 01 75 08 26 ff 00 15 00 85 06 95 3f 09 01 91 02 85 05 95 3f 09 01 81 02 c0 05 0d 09 04 a1 01 85 81 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 07 81 03 75 08 09 51 95 01 81 02 05 01 65 11 55 0f 35 00 46 b0 01 26 80 07 75 10 09 30 81 02 46 f3 00 26 38 04 09 31 81 02 05 0d 09 48 09 49 26 ff 00 95 02 75 08 81 02 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 07 81 03 75 08 09 51 95 01 81 02 05 01 65 11 55 0f 35 00 46 b0 01 26 80 07 75 10 09 30 81 02 46 f3 00 26 38 04 09 31 81 02 05 0d 09 48 09 49 26 ff 00 95 02 75 08 81 02 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 07 81 03 75 08 09 51 95 01 81 02 05 01 65 11 55 0f 35 00 46 b0 01 26 80 07 75 10 09 30 81 02 46 f3 00 26 38 04 09 31 81 02 05 0d 09 48 09 49 26 ff 00 95 02 75 08 81 02 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 07 81 03 75 08 09 51 95 01 81 02 05 01 65 11 55 0f 35 00 46 b0 01 26 80 07 75 10 09 30 81 02 46 f3 00 26 38 04 09 31 81 02 05 0d 09 48 09 49 26 ff 00 95 02 75 08 81 02 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 07 81 03 75 08 09 51 95 01 81 02 05 01 65 11 55 0f 35 00 46 b0 01 26 80 07 75 10 09 30 81 02 46 f3 00 26 38 04 09 31 81 02 05 0d 09 48 09 49 26 ff 00 95 02 75 08 81 02 c0 05 0d 09 56 55 0c 66 01 10 47 ff ff 00 00 27 ff ff 00 00 75 10 95 01 81 02 09 54 95 01 75 08 15 00 25 0a 81 02 85 84 09 55 b1 02 85 87 06 00 ff 09 c5 15 00 26 ff 00 75 08 96 00 01 b1 02 c0 09 0e a1 01 85 83 09 23 a1 02 09 52 09 53 15 00 25 0a 75 08 95 02 b1 02 c0 c0 05 01 09 02 a1 01 09 01 a1 00 85 80 05 09 19 01 29 01 15 00 25 01 95 01 75 01 81 02 95 01 75 07 81 01 05 01 65 11 55 0f 09 30 26 80 07 35 00 46 66 00 75 10 95 01 81 02 09 31 26 38 04 35 00 46 4d 00 81 02 c0 c0")


class Testsynaptics_06cb_1d10(BaseTest.TestMultitouch):
    def _create_device(self):
        return Digitizer("uhid test synaptics_06cb_1d10", rdesc="572 05 01 09 02 a1 01 85 02 09 01 a1 00 05 09 19 01 29 02 15 00 25 01 75 01 95 02 81 02 95 06 81 03 05 01 09 30 09 31 75 08 95 02 15 81 25 7f 35 81 45 7f 55 0e 65 11 81 06 c0 c0 05 0d 09 04 a1 01 85 01 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 07 81 03 75 08 09 51 15 01 26 ff 00 95 01 81 42 05 01 15 00 26 3c 0c 75 10 55 0e 65 11 09 30 35 12 46 2a 0c 81 02 09 31 15 00 26 f1 06 35 12 46 df 06 81 02 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 07 81 03 75 08 09 51 15 01 26 ff 00 95 01 81 42 05 01 15 00 26 3c 0c 75 10 55 0e 65 11 09 30 35 12 46 2a 0c 81 02 09 31 15 00 26 f1 06 35 12 46 df 06 81 02 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 07 81 03 75 08 09 51 15 01 26 ff 00 95 01 81 42 05 01 15 00 26 3c 0c 75 10 55 0e 65 11 09 30 35 12 46 2a 0c 81 02 09 31 15 00 26 f1 06 35 12 46 df 06 81 02 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 07 81 03 75 08 09 51 15 01 26 ff 00 95 01 81 42 05 01 15 00 26 3c 0c 75 10 55 0e 65 11 09 30 35 12 46 2a 0c 81 02 09 31 15 00 26 f1 06 35 12 46 df 06 81 02 c0 05 0d 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 95 07 81 03 75 08 09 51 15 01 26 ff 00 95 01 81 42 05 01 15 00 26 3c 0c 75 10 55 0e 65 11 09 30 35 12 46 2a 0c 81 02 09 31 15 00 26 f1 06 35 12 46 df 06 81 02 c0 05 0d 05 0d 55 0c 66 01 10 47 ff ff 00 00 27 ff ff 00 00 75 10 95 01 09 56 81 02 09 54 95 01 75 08 15 00 25 0f 81 02 85 08 09 55 b1 03 85 07 06 00 ff 09 c5 15 00 26 ff 00 75 08 96 00 01 b1 02 c0 06 00 ff 09 01 a1 01 85 09 09 02 15 00 26 ff 00 75 08 95 3f 91 02 85 0a 09 03 15 00 26 ff 00 75 08 95 05 91 02 85 0b 09 04 15 00 26 ff 00 75 08 95 3d 81 02 85 0c 09 05 15 00 26 ff 00 75 08 95 01 81 02 85 0f 09 06 15 00 26 ff 00 75 08 95 01 b1 02 c0")


if __name__ == "__main__":
    main(sys.argv[1:])
