#!/bin/env python3
# -*- coding: utf-8 -*-
#
# Hid tools / tests/mouse.py: unittest for mice devices
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
from base import main, setUpModule, tearDownModule  # noqa


class MouseData(object):
    pass


class Mouse(base.UHIDTest):
    def __init__(self):
        rdesc = [
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
        ]
        super(Mouse, self).__init__("uhid test simple", rdesc=rdesc)
        self.info = 3, 1, 2
        self.left = False
        self.right = False
        self.middle = False
        self.create_kernel_device()

    def format_report(self, x, y, buttons=None, use_rdesc=True):
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
        x = max(-127, min(127, x))
        y = max(-127, min(127, y))
        if use_rdesc:
            mouse = MouseData()
            mouse.b1 = int(l)
            mouse.b2 = int(r)
            mouse.b3 = int(m)
            mouse.x = x
            mouse.y = y
            return super(Mouse, self).format_report(mouse)

        button_mask = sum(1 << i for i, b in enumerate([l, r, m]) if b)
        x = base.to_twos_comp(x, 8)
        y = base.to_twos_comp(y, 8)
        return [button_mask, x, y]

    def event(self, x, y, buttons=None):
        r = self.format_report(x, y, buttons)
        self.call_input_event(r)


class TestMouse(base.BaseTestCase.TestUhid):
    def test_creation(self):
        with Mouse() as uhdev:
            while len(uhdev.input_nodes) == 0:
                uhdev.process_one_event(10)
            self.assertIsNotNone(uhdev.evdev)
            self.assertEqual(uhdev.evdev.name, uhdev.name)
            self.assertEqual(len(uhdev.next_sync_events()), 0)
            uhdev.destroy()
            while uhdev.opened:
                if uhdev.process_one_event(100) == 0:
                    break
            with self.assertRaises(OSError):
                uhdev.evdev.fd.read()

    def test_rdesc(self):
        with Mouse() as uhdev:
            event = (0, 0, (None, None, None))
            self.assertEqual(uhdev.format_report(*event, True),
                             uhdev.format_report(*event, False))

            event = (0, 0, (None, True, None))
            self.assertEqual(uhdev.format_report(*event, True),
                             uhdev.format_report(*event, False))

            event = (0, 0, (True, True, None))
            self.assertEqual(uhdev.format_report(*event, True),
                             uhdev.format_report(*event, False))

            event = (0, 0, (False, False, False))
            self.assertEqual(uhdev.format_report(*event, True),
                             uhdev.format_report(*event, False))

            event = (1, 0, (True, False, True))
            self.assertEqual(uhdev.format_report(*event, True),
                             uhdev.format_report(*event, False))

            event = (-1, 0, (True, False, True))
            self.assertEqual(uhdev.format_report(*event, True),
                             uhdev.format_report(*event, False))

            event = (-5, 5, (True, False, True))
            self.assertEqual(uhdev.format_report(*event, True),
                             uhdev.format_report(*event, False))

            event = (0, -128, (True, False, True))
            self.assertEqual(uhdev.format_report(*event, True),
                             uhdev.format_report(*event, False))

    def test_buttons(self):
        with Mouse() as uhdev:
            while len(uhdev.input_nodes) == 0:
                uhdev.process_one_event(10)

            syn_event = self.syn_event
            key_event = self.key_event
            abs_event = self.abs_event
            rel_event = self.rel_event
            msc_event = self.msc_event

            uhdev.event(0, 0, (None, True, None))
            expected_event = libevdev.InputEvent("EV_KEY", "BTN_RIGHT", 1)
            events = uhdev.next_sync_events()
            self.assertInputEventsIn((syn_event, expected_event), events)
            self.assertEqual(uhdev.evdev.event_value("EV_KEY", "BTN_RIGHT"), 1)

            uhdev.event(0, 0, (None, False, None))
            expected_event = libevdev.InputEvent("EV_KEY", "BTN_RIGHT", 0)
            events = uhdev.next_sync_events()
            self.assertInputEventsIn((syn_event, expected_event), events)
            self.assertEqual(uhdev.evdev.event_value("EV_KEY", "BTN_RIGHT"), 0)

            uhdev.event(0, 0, (None, None, True))
            expected_event = libevdev.InputEvent("EV_KEY", "BTN_MIDDLE", 1)
            events = uhdev.next_sync_events()
            self.assertInputEventsIn((syn_event, expected_event), events)
            self.assertEqual(uhdev.evdev.event_value("EV_KEY", "BTN_MIDDLE"), 1)

            uhdev.event(0, 0, (None, None, False))
            expected_event = libevdev.InputEvent("EV_KEY", "BTN_MIDDLE", 0)
            events = uhdev.next_sync_events()
            self.assertInputEventsIn((syn_event, expected_event), events)
            self.assertEqual(uhdev.evdev.event_value("EV_KEY", "BTN_MIDDLE"), 0)

            uhdev.event(0, 0, (True, None, None))
            expected_event = libevdev.InputEvent("EV_KEY", "BTN_LEFT", 1)
            events = uhdev.next_sync_events()
            self.assertInputEventsIn((syn_event, expected_event), events)
            self.assertEqual(uhdev.evdev.event_value("EV_KEY", "BTN_LEFT"), 1)

            uhdev.event(0, 0, (False, None, None))
            expected_event = libevdev.InputEvent("EV_KEY", "BTN_LEFT", 0)
            events = uhdev.next_sync_events()
            self.assertInputEventsIn((syn_event, expected_event), events)
            self.assertEqual(uhdev.evdev.event_value("EV_KEY", "BTN_LEFT"), 0)

            uhdev.event(0, 0, (True, True, None))
            expected_event0 = libevdev.InputEvent("EV_KEY", "BTN_LEFT", 1)
            expected_event1 = libevdev.InputEvent("EV_KEY", "BTN_RIGHT", 1)
            events = uhdev.next_sync_events()
            self.assertInputEventsIn((syn_event, expected_event0, expected_event1), events)
            self.assertEqual(uhdev.evdev.event_value("EV_KEY", "BTN_RIGHT"), 1)
            self.assertEqual(uhdev.evdev.event_value("EV_KEY", "BTN_LEFT"), 1)

            uhdev.event(0, 0, (False, None, None))
            expected_event = libevdev.InputEvent("EV_KEY", "BTN_LEFT", 0)
            events = uhdev.next_sync_events()
            self.assertInputEventsIn((syn_event, expected_event), events)
            self.assertEqual(uhdev.evdev.event_value("EV_KEY", "BTN_RIGHT"), 1)
            self.assertEqual(uhdev.evdev.event_value("EV_KEY", "BTN_LEFT"), 0)

            uhdev.event(0, 0, (None, False, None))
            expected_event = libevdev.InputEvent("EV_KEY", "BTN_RIGHT", 0)
            events = uhdev.next_sync_events()
            self.assertInputEventsIn((syn_event, expected_event), events)
            self.assertEqual(uhdev.evdev.event_value("EV_KEY", "BTN_RIGHT"), 0)
            self.assertEqual(uhdev.evdev.event_value("EV_KEY", "BTN_LEFT"), 0)

            uhdev.destroy()

    def test_relative(self):
        with Mouse() as uhdev:
            while len(uhdev.input_nodes) == 0:
                uhdev.process_one_event(10)

            syn_event = self.syn_event
            key_event = self.key_event
            abs_event = self.abs_event
            rel_event = self.rel_event
            msc_event = self.msc_event

            uhdev.event(0, -1, (None, None, None))
            expected_event = libevdev.InputEvent("EV_REL", "REL_Y", -1)
            events = uhdev.next_sync_events()
            self.assertInputEvents((syn_event, expected_event), events)

            uhdev.event(1, 0, (None, None, None))
            expected_event = libevdev.InputEvent("EV_REL", "REL_X", 1)
            events = uhdev.next_sync_events()
            self.assertInputEvents((syn_event, expected_event), events)

            uhdev.event(-1, 2, (None, None, None))
            expected_event0 = libevdev.InputEvent("EV_REL", "REL_X", -1)
            expected_event1 = libevdev.InputEvent("EV_REL", "REL_Y", 2)
            events = uhdev.next_sync_events()
            self.assertInputEvents((syn_event, expected_event0, expected_event1), events)

            uhdev.destroy()


if __name__ == "__main__":
    main(sys.argv[1:])
