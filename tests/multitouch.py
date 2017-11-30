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
import hid
import parse_rdesc
import sys
import unittest
from base import main, setUpModule, tearDownModule  # noqa


class Touch(object):
    def __init__(self, id, x, y):
        self.contactid = id
        self.x = x
        self.y = y
        self.tipswitch = False
        self.confidence = False
        self.pressure = 0
        self.azimuth = 0
        self.inrange = False
        self.width = 0
        self.height = 0


class Pen(Touch):
    def __init__(self, x, y):
        super(Pen, self).__init__(x, y)
        self.barrel = False
        self.invert = False
        self.eraser = False
        self.x_tilt = False
        self.y_tilt = False
        self.twist = 0


class Usage(object):
    def __init__(self, page, name, size):
        self.page = page
        self.name = name
        self.size = size
        self.min = 0
        self.max = (1 << size) - 1

    def __repr__(self):
        return f'usage {self.page}/{self.name}'


class InputUsage(Usage):
    def __init__(self, page, name, size=1, type='abs'):
        super(InputUsage, self).__init__(page, name, size)
        self.type = type

    def close(self, rdesc):
        if self.type == 'abs':
            rdesc.extend((0x81, 0x02))  # Input (Data,Var,Abs)
        elif self.type == 'rel':
            rdesc.extend((0x81, 0x06))  # Input (Data,Var,Rel)
        elif self.type == 'padding':
            rdesc.extend((0x81, 0x03))  # Input (Cnst,Var,Abs)


class FeatureUsage(Usage):
    def __init__(self, page, name, size=1):
        super(FeatureUsage, self).__init__(page, name, size)

    def close(self, rdesc):
        rdesc.extend((0xb1, 0x02))  # Feature (Data,Var,Abs)


class Digitizer(base.UHIDTest):
    def __init__(self, name, usages, physical_maxs, logical_maxs):
        super(Digitizer, self).__init__("uhid test simple")
        self.info = 3, 1, 2
        # subclasses need to set self.max_slots for 'Contact Max'
        self.scantime = 0
        self.physical_maxs = physical_maxs
        self.logical_maxs = logical_maxs
        self.usages = usages
        self.cur_usage_page = None
        self.cur_usage = None
        self.cur_size = None
        self.cur_count = None
        self.cur_logical_min = None
        self.cur_logical_max = None
        self.cur_physical_min = None
        self.cur_physical_max = None
        self.rdesc = self.parse_usages()
        self.create_kernel_device()

    def append_item(self, type, usage, value, rdesc):
        bit_size = len(f'{value + 1:x}') * 4
        tag = hid.hid_items[type][usage]
        size = 0
        v_count = 0
        if bit_size <= 8:
            size = 1
            v_count = 1
        elif bit_size <= 16:
            size = 2
            v_count = 2
        else:
            size = 3
            v_count = 4
        rdesc.append(tag | size)
        if usage == "Unit Exponent" and value < 0:
                value += 16
        value = base.to_twos_comp(value, v_count * 8)
        for i in range(v_count):
            rdesc.append((value >> (i * 8)) & 0xff)

    def append_usage(self, usage_page, usage, rdesc):
        up = hid.usage_pages[usage_page]
        if usage_page != self.cur_usage_page:
            self.append_item('Global', 'Usage Page', up, rdesc)
            self.cur_usage_page = usage_page
        if usage != self.cur_usage:
            self.append_item('Local', 'Usage', hid.usages[up][3][usage], rdesc)
            self.cur_usage = usage

    def append_size(self, value, rdesc):
        if value == self.cur_size:
            return
        self.append_item('Global', 'Report Size', value, rdesc)
        self.cur_size = value

    def append_count(self, value, rdesc):
        if value == self.cur_count:
            return
        self.append_item('Global', 'Report Count', value, rdesc)
        self.cur_count = value

    def append_logical_min(self, value, rdesc):
        if value == self.cur_logical_min:
            return
        self.append_item('Global', 'Logical Minimum', value, rdesc)
        self.cur_logical_min = value

    def append_logical_max(self, value, rdesc):
        if value == self.cur_logical_max:
            return
        self.append_item('Global', 'Logical Maximum', value, rdesc)
        self.cur_logical_max = value

    def append_physical_min(self, value, rdesc):
        if value == self.cur_physical_min:
            return
        self.append_item('Global', 'Physical Minimum', value, rdesc)
        self.cur_physical_min = value

    def append_physical_max(self, value, rdesc):
        if value == self.cur_physical_max:
            return
        self.append_item('Global', 'Physical Maximum', value, rdesc)
        self.cur_physical_max = value

    def process_usage(self, usage, rdesc):
        if isinstance(usage, list):
            if self.application in ('Touch Screen', 'Touch Pad'):
                self.append_usage('Digitizers', 'Finger', rdesc)
            else:
                self.append_usage('Digitizers', 'Stylus')
            rdesc.extend((0xa1, 0x02))  # .Collection (Logical)
            for d in usage:
                self.process_usage(d, rdesc)
            rdesc.append(0xc0)  # End Collection
        elif usage.page is None and usage.name == 'CertificationBlob':
            rdesc.extend((
                0x06, 0x00, 0xff,  # ..Usage Page (Vendor Defined Page 1)
                0x09, 0xc5,        # ..Usage (Vendor Usage 0xc5)
                0x15, 0x00,        # ..Logical Minimum (0)
                0x26, 0xff, 0x00,  # ..Logical Maximum (255)
                0x75, 0x08,        # ..Report Size (8)
                0x96, 0x00, 0x01,  # ..Report Count (256)
                0xb1, 0x02,        # ..Feature (Data,Var,Abs)
            ))
        else:
            self.append_size(usage.size, rdesc)
            self.append_count(1, rdesc)
            if usage.name == 'X':
                self.append_item('Global', 'Unit Exponent', -1, rdesc)
                self.append_item('Global', 'Unit', 0x11, rdesc)  # Unit (Centimeter,SILinear)
                self.append_logical_min(0, rdesc)
                self.append_logical_max(self.logical_maxs[0], rdesc)
                self.append_physical_min(0, rdesc)
                self.append_physical_max(self.physical_maxs[0], rdesc)
            elif usage.name == 'Y':
                self.append_logical_min(0, rdesc)
                self.append_logical_max(self.logical_maxs[1], rdesc)
                self.append_physical_min(0, rdesc)
                self.append_physical_max(self.physical_maxs[1], rdesc)
            elif usage.name == 'Contact Max':
                self.append_logical_min(0, rdesc)
                self.append_logical_max(self.max_slots, rdesc)
            elif usage.name == 'Scan Time':
                self.append_item('Global', 'Unit Exponent', -4, rdesc)
                self.append_item('Global', 'Unit', 0x1001, rdesc)  # Unit (Seconds,SILinear)
                self.append_logical_min(usage.min, rdesc)
                self.append_logical_max(usage.max, rdesc)
                self.append_physical_min(usage.min, rdesc)
                self.append_physical_max(usage.max, rdesc)
            else:
                self.append_logical_min(usage.min, rdesc)
                self.append_logical_max(usage.max, rdesc)
            self.append_usage(usage.page, usage.name, rdesc)
            usage.close(rdesc)

    def parse_usages(self):
        self.cur_usage_page = None
        self.cur_usage = None
        self.application = None
        rdesc = []
        for k, v in self.usages.items():
            app, descr = v
            self.application = app
            self.append_usage('Digitizers', app, rdesc)
            rdesc.extend((0xa1, 0x01))  # Collection (Application)
            rdesc.extend((0x85, k))     # .Report ID (k)
            # process descr
            for d in descr:
                self.process_usage(d, rdesc)
            rdesc.append(0xc0)  # End Collection
        # self.parsed_rdesc = parse_rdesc.parse_rdesc(rdesc, sys.stdout)
        self.parsed_rdesc = parse_rdesc.parse_rdesc(rdesc)
        return rdesc

    def process_event(self, slots, usage, r):
        cur_offset = self.cur_offset
        if isinstance(usage, list):
            for u in usage:
                self.process_event(slots, u, r)
            return

        if not isinstance(usage, InputUsage):
            return

        cur_offset %= 8

        if usage.type == 'padding':
            self.cur_offset += usage.size
            return

        if usage.name in self.prev_seen_usages:
            if len(slots) > 0:
                slots.pop(0)
            self.prev_seen_usages.clear()

        value = 0
        field = usage.name.replace(' ', '').lower()
        if field in 'contactid x y tipswitch confidence pressure azimuth inrange width height':
            if len(slots) > 0:
                value = getattr(slots[0], field)
        else:
            value = getattr(self, field)
        n_bytes = int((usage.size + 7) / 8)
        for i in range(n_bytes):
            r.append((value >> (i * 8)) & 0xff)
        self.prev_seen_usages.append(usage.name)
        self.cur_offset += usage.size
        return

    def event(self, slots):
        self.scantime += 1
        r = [0x01]
        self.prev_seen_usages = []
        self.cur_offset = 0
        self.contactcount = len(slots)
        for u in self.usages[1][1]:
            self.process_event(slots, u, r)
        self.call_input_event(r)
        return r


class MinWin8TSParallel(Digitizer):
    def __init__(self):
        self.max_slots = 2
        finger_usages = [
            InputUsage('Digitizers', 'Tip Switch'),
            InputUsage('Digitizers', 'Tip Switch', 7, 'padding'),
            InputUsage('Digitizers', 'Contact Id', 8),
            InputUsage('Generic Desktop', 'X', 16),
            InputUsage('Generic Desktop', 'Y', 16),
        ]
        usages = {
            1: ('Touch Screen',
                [
                    *([finger_usages] * self.max_slots),
                    InputUsage('Digitizers', 'Scan Time', 16),
                    InputUsage('Digitizers', 'Contact Count', 8),
                ]),
            2: ('Touch Screen',
                [
                    FeatureUsage('Digitizers', 'Contact Max', 8),
                ]),
            68: ('Touch Screen',
                 [
                     Usage(None, 'CertificationBlob', 8),
                 ]),
        }
        super(MinWin8TSParallel, self).__init__("uhid test simple",
                                                usages,
                                                (120, 90),
                                                (4095, 4095))


class _TestMultitouch(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        super(_TestMultitouch, self).__init__(methodName)
        self.__create_device = self._create_device

    def _create_device(self):
        raise Exception("please reimplement me in subclasses")

    def test_mt_creation(self):
        with self.__create_device() as uhdev:
            while not uhdev.opened:
                uhdev.process_one_event(100)
            self.assertIsNotNone(uhdev.evdev)
            self.assertEqual(uhdev.evdev.name, uhdev.name)
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
            t0 = Touch(1, 5, 5)
            t0.tipswitch = 1
            print()
            r = uhdev.event([t0])
            print('r is', r)
            events = uhdev.next_sync_events()
            print([(e.type_name, e.code_name, e.value) for e in events])
            t0.tipswitch = 0
            r = uhdev.event([t0])
            print('r is', r)
            events = uhdev.next_sync_events()
            print([(e.type_name, e.code_name, e.value) for e in events])
            uhdev.destroy()


class TestMinWin8TSParallel(_TestMultitouch):
    def _create_device(self):
        return MinWin8TSParallel()


if __name__ == "__main__":
    main(sys.argv[1:])
