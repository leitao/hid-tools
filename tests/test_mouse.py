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

import base
import libevdev
import sys
import hidtools.hid
from base import main, setUpModule, tearDownModule  # noqa


class MouseData(object):
    pass

class BaseMouse(base.UHIDTestDevice):
    def __init__(self, name, rdesc, info):
        super().__init__(name, rdesc=rdesc)
        self.info = info
        self.application = 'Mouse'
        self.left = False
        self.right = False
        self.middle = False
        self.create_kernel_device()

    def fake_report(self, x, y, buttons):
        if buttons is not None:
            l, r, m = buttons
            if l is None:
                l = self.left
            if r is None:
                r = self.right
            if m is None:
                m = self.middle
        else:
            l = self.left
            r = self.right
            m = self.middle

        button_mask = sum(1 << i for i, b in enumerate([l, r, m]) if b)
        x = max(-127, min(127, x))
        y = max(-127, min(127, y))
        x = base.to_twos_comp(x, 8)
        y = base.to_twos_comp(y, 8)
        return [button_mask, x, y]

    def format_report(self, x, y, buttons=None, reportID=None):
        if buttons is not None:
            l, r, m = buttons
            if l is not None:
                self.left = l
            if r is not None:
                self.right = r
            if m is not None:
                self.middle = m
        l = self.left
        r = self.right
        m = self.middle

        mouse = MouseData()
        mouse.b1 = int(l)
        mouse.b2 = int(r)
        mouse.b3 = int(m)
        mouse.x = x
        mouse.y = y
        return super().format_report(mouse, reportID=reportID)

    def event(self, x, y, buttons=None):
        r = self.format_report(x, y, buttons)
        self.call_input_event(r)
        return [r]

    @property
    def evdev(self):
        if self.application not in self.input_nodes:
            return None

        return self.input_nodes[self.application]


class MIDongleMIWirelessMouse(BaseMouse):
    def __init__(self, name):
        super().__init__(name,
                         rdesc='05 01 09 02 a1 01 85 01 09 01 a1 00 95 05 75 01 05 09 19 01 29 05 15 00 25 01 81 02 95 01 75 03 81 01 75 08 95 01 05 01 09 38 15 81 25 7f 81 06 05 0c 0a 38 02 95 01 81 06 c0 85 02 09 01 a1 00 75 0c 95 02 05 01 09 30 09 31 16 01 f8 26 ff 07 81 06 c0 c0 05 0c 09 01 a1 01 85 03 15 00 25 01 75 01 95 01 09 cd 81 06 0a 83 01 81 06 09 b5 81 06 09 b6 81 06 09 ea 81 06 09 e9 81 06 0a 25 02 81 06 0a 24 02 81 06 c0',
                         info=(0x3, 0x2717, 0x003b))

    def event(self, x, y, buttons=None):
        # this mouse spreads the relative pointer and the mouse buttons
        # onto 2 distinct reports
        rs = []
        r = self.format_report(x, y, buttons, reportID=1)
        self.call_input_event(r)
        rs.append(r)
        r = self.format_report(x, y, buttons, reportID=2)
        self.call_input_event(r)
        rs.append(r)
        return rs


class BaseTest:
    class TestMouse(base.BaseTestCase.TestUhid):
        def create_mouse(self):
            raise Exception('please reimplement me in subclasses')

        def test_creation(self):
            """Make sure the device gets processed by the kernel and creates
            the expected application input node.

            If this fail, there is something wrong in the device report
            descriptors."""
            with self.create_mouse() as uhdev:
                while uhdev.application not in uhdev.input_nodes:
                    uhdev.dispatch(10)
                self.assertIsNotNone(uhdev.evdev)
                self.assertEqual(uhdev.evdev.name, uhdev.name)
                self.assertEqual(len(uhdev.next_sync_events()), 0)
                uhdev.destroy()
                while uhdev.opened:
                    if uhdev.dispatch(100) == 0:
                        break
                with self.assertRaises(OSError):
                    uhdev.evdev.fd.read()

        def test_buttons(self):
            """check for button reliability."""
            with self.create_mouse() as uhdev:
                while uhdev.application not in uhdev.input_nodes:
                    uhdev.dispatch(10)

                syn_event = self.syn_event

                r = uhdev.event(0, 0, (None, True, None))
                expected_event = libevdev.InputEvent(libevdev.EV_KEY.BTN_RIGHT, 1)
                events = uhdev.next_sync_events()
                self.debug_reports(r, uhdev); print(events)
                self.assertInputEventsIn((syn_event, expected_event), events)
                self.assertEqual(uhdev.evdev.value[libevdev.EV_KEY.BTN_RIGHT], 1)

                r = uhdev.event(0, 0, (None, False, None))
                expected_event = libevdev.InputEvent(libevdev.EV_KEY.BTN_RIGHT, 0)
                events = uhdev.next_sync_events()
                self.debug_reports(r, uhdev); print(events)
                self.assertInputEventsIn((syn_event, expected_event), events)
                self.assertEqual(uhdev.evdev.value[libevdev.EV_KEY.BTN_RIGHT], 0)

                r = uhdev.event(0, 0, (None, None, True))
                expected_event = libevdev.InputEvent(libevdev.EV_KEY.BTN_MIDDLE, 1)
                events = uhdev.next_sync_events()
                self.debug_reports(r, uhdev); print(events)
                self.assertInputEventsIn((syn_event, expected_event), events)
                self.assertEqual(uhdev.evdev.value[libevdev.EV_KEY.BTN_MIDDLE], 1)

                r = uhdev.event(0, 0, (None, None, False))
                expected_event = libevdev.InputEvent(libevdev.EV_KEY.BTN_MIDDLE, 0)
                events = uhdev.next_sync_events()
                self.debug_reports(r, uhdev); print(events)
                self.assertInputEventsIn((syn_event, expected_event), events)
                self.assertEqual(uhdev.evdev.value[libevdev.EV_KEY.BTN_MIDDLE], 0)

                r = uhdev.event(0, 0, (True, None, None))
                expected_event = libevdev.InputEvent(libevdev.EV_KEY.BTN_LEFT, 1)
                events = uhdev.next_sync_events()
                self.debug_reports(r, uhdev); print(events)
                self.assertInputEventsIn((syn_event, expected_event), events)
                self.assertEqual(uhdev.evdev.value[libevdev.EV_KEY.BTN_LEFT], 1)

                r = uhdev.event(0, 0, (False, None, None))
                expected_event = libevdev.InputEvent(libevdev.EV_KEY.BTN_LEFT, 0)
                events = uhdev.next_sync_events()
                self.debug_reports(r, uhdev); print(events)
                self.assertInputEventsIn((syn_event, expected_event), events)
                self.assertEqual(uhdev.evdev.value[libevdev.EV_KEY.BTN_LEFT], 0)

                r = uhdev.event(0, 0, (True, True, None))
                expected_event0 = libevdev.InputEvent(libevdev.EV_KEY.BTN_LEFT, 1)
                expected_event1 = libevdev.InputEvent(libevdev.EV_KEY.BTN_RIGHT, 1)
                events = uhdev.next_sync_events()
                self.debug_reports(r, uhdev); print(events)
                self.assertInputEventsIn((syn_event, expected_event0, expected_event1), events)
                self.assertEqual(uhdev.evdev.value[libevdev.EV_KEY.BTN_RIGHT], 1)
                self.assertEqual(uhdev.evdev.value[libevdev.EV_KEY.BTN_LEFT], 1)

                r = uhdev.event(0, 0, (False, None, None))
                expected_event = libevdev.InputEvent(libevdev.EV_KEY.BTN_LEFT, 0)
                events = uhdev.next_sync_events()
                self.debug_reports(r, uhdev); print(events)
                self.assertInputEventsIn((syn_event, expected_event), events)
                self.assertEqual(uhdev.evdev.value[libevdev.EV_KEY.BTN_RIGHT], 1)
                self.assertEqual(uhdev.evdev.value[libevdev.EV_KEY.BTN_LEFT], 0)

                r = uhdev.event(0, 0, (None, False, None))
                expected_event = libevdev.InputEvent(libevdev.EV_KEY.BTN_RIGHT, 0)
                events = uhdev.next_sync_events()
                self.debug_reports(r, uhdev); print(events)
                self.assertInputEventsIn((syn_event, expected_event), events)
                self.assertEqual(uhdev.evdev.value[libevdev.EV_KEY.BTN_RIGHT], 0)
                self.assertEqual(uhdev.evdev.value[libevdev.EV_KEY.BTN_LEFT], 0)


        def test_relative(self):
            """Check for relative events."""
            with self.create_mouse() as uhdev:
                while uhdev.application not in uhdev.input_nodes:
                    uhdev.dispatch(10)

                syn_event = self.syn_event

                r = uhdev.event(0, -1)
                expected_event = libevdev.InputEvent(libevdev.EV_REL.REL_Y, -1)
                events = uhdev.next_sync_events()
                self.debug_reports(r, uhdev); print(events)
                self.assertInputEvents((syn_event, expected_event), events)

                r = uhdev.event(1, 0)
                expected_event = libevdev.InputEvent(libevdev.EV_REL.REL_X, 1)
                events = uhdev.next_sync_events()
                self.debug_reports(r, uhdev); print(events)
                self.assertInputEvents((syn_event, expected_event), events)

                r = uhdev.event(-1, 2)
                expected_event0 = libevdev.InputEvent(libevdev.EV_REL.REL_X, -1)
                expected_event1 = libevdev.InputEvent(libevdev.EV_REL.REL_Y, 2)
                events = uhdev.next_sync_events()
                self.debug_reports(r, uhdev); print(events)
                self.assertInputEvents((syn_event, expected_event0, expected_event1), events)



class TestSimpleMouse(BaseTest.TestMouse):
    def create_mouse(self):
        return BaseMouse("uhid test simple",
                         rdesc=[
                             0x05, 0x01,  # .Usage Page (Generic Desktop)        0
                             0x09, 0x02,  # .Usage (Mouse)                       2
                             0xa1, 0x01,  # .Collection (Application)            4
                             0x09, 0x02,  # ..Usage (Mouse)                      6
                             0xa1, 0x02,  # ..Collection (Logical)               8
                             0x09, 0x01,  # ...Usage (Pointer)                   10
                             0xa1, 0x00,  # ...Collection (Physical)             12
                             0x05, 0x09,  # ....Usage Page (Button)              14
                             0x19, 0x01,  # ....Usage Minimum (1)                16
                             0x29, 0x03,  # ....Usage Maximum (3)                18
                             0x15, 0x00,  # ....Logical Minimum (0)              20
                             0x25, 0x01,  # ....Logical Maximum (1)              22
                             0x75, 0x01,  # ....Report Size (1)                  24
                             0x95, 0x03,  # ....Report Count (3)                 26
                             0x81, 0x02,  # ....Input (Data,Var,Abs)             28
                             0x75, 0x05,  # ....Report Size (5)                  30
                             0x95, 0x01,  # ....Report Count (1)                 32
                             0x81, 0x03,  # ....Input (Cnst,Var,Abs)             34
                             0x05, 0x01,  # ....Usage Page (Generic Desktop)     36
                             0x09, 0x30,  # ....Usage (X)                        38
                             0x09, 0x31,  # ....Usage (Y)                        40
                             0x15, 0x81,  # ....Logical Minimum (-127)           42
                             0x25, 0x7f,  # ....Logical Maximum (127)            44
                             0x75, 0x08,  # ....Report Size (8)                  46
                             0x95, 0x02,  # ....Report Count (2)                 48
                             0x81, 0x06,  # ....Input (Data,Var,Rel)             50
                             0xc0,        # ...End Collection                    52
                             0xc0,        # ..End Collection                     53
                             0xc0,        # .End Collection                      54
                         ],
                         info=(3, 1, 2))

    def test_rdesc(self):
        """Check that the testsuite actually manages to format the
        reports according to the report descriptors.
        No kernel device is used here"""
        with self.create_mouse() as uhdev:
            event = (0, 0, (None, None, None))
            self.assertEqual(uhdev.fake_report(*event),
                             uhdev.format_report(*event))

            event = (0, 0, (None, True, None))
            self.assertEqual(uhdev.fake_report(*event),
                             uhdev.format_report(*event))

            event = (0, 0, (True, True, None))
            self.assertEqual(uhdev.fake_report(*event),
                             uhdev.format_report(*event))

            event = (0, 0, (False, False, False))
            self.assertEqual(uhdev.fake_report(*event),
                             uhdev.format_report(*event))

            event = (1, 0, (True, False, True))
            self.assertEqual(uhdev.fake_report(*event),
                             uhdev.format_report(*event))

            event = (-1, 0, (True, False, True))
            self.assertEqual(uhdev.fake_report(*event),
                             uhdev.format_report(*event))

            event = (-5, 5, (True, False, True))
            self.assertEqual(uhdev.fake_report(*event),
                             uhdev.format_report(*event))

            event = (-127, 127, (True, False, True))
            self.assertEqual(uhdev.fake_report(*event),
                             uhdev.format_report(*event))

            event = (0, -128, (True, False, True))
            with self.assertRaises(hidtools.hid.RangeError):
                uhdev.format_report(*event)


class TestMiMouse(BaseTest.TestMouse):
    def create_mouse(self):
        return MIDongleMIWirelessMouse("uhid test MI Dongle MI Wireless Mouse")


if __name__ == "__main__":
    main(sys.argv[1:])
