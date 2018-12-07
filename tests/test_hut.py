#!/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (c) 2018 Red Hat, Inc.
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

import unittest
from hidtools.hut import HUT


class TestHUT(unittest.TestCase):
    pages = {
        0x00: 'Undefined',
        0x01: 'Generic Desktop',
        0x02: 'Simulation Controls',
        0x03: 'VR Controls',
        0x04: 'Sports Controls',
        0x05: 'Gaming Controls',
        0x06: 'Generic Device Controls',
        0x07: 'Keyboard',
        0x08: 'LEDs',
        0x09: 'Button',
        0x0a: 'Ordinals',
        0x0b: 'Telephony Devices',
        0x0c: 'Consumer Devices',
        0x0d: 'Digitizers',
        0x0e: 'Haptic',
        0x10: 'Unicode',
        0x14: 'Auxiliary Display',
        0x20: 'Sensor',
        0x40: 'Medical Instruments',
        0x80: 'Monitor',
        0x81: 'Monitor Enumerated Values',
        0x82: 'VESA Virtual Controls',
        0x83: 'VESA Command',
        0x84: 'Power Device',
        0x85: 'Battery System',
        0x8c: 'Bar Code Scanner',
        0x8d: 'Scale',
        0x8e: 'Magnetic Stripe Reading',
        0x90: 'Camera Control',
        0x91: 'Arcade Page OAAF',
        0x92: 'Gaming Device',
        0xF1D0: 'FIDO Alliance',
        0xff00: 'Vendor Defined Page 1',
        0xff0d: 'Wacom',
    }

    def test_hut_exists(self):
        self.assertIsNotNone(HUT)

    def test_hut_size(self):
        # Update this test when a new Usage Page is added
        self.assertEqual(len(HUT), 34)

    def test_usage_pages(self):
        pages = self.pages
        empty_pages = ['Unicode', 'Power Device', 'Battery System', 'Gaming Device']

        for page_id, name in pages.items():
            page = HUT[page_id]
            self.assertEqual(page.page_id, page_id)
            self.assertEqual(page.page_name, name)
            print(page, page.page_name)
            if page.page_name in empty_pages:
                self.assertEqual(dict(page.from_name.items()), {})
                self.assertEqual(dict(page.from_usage.items()), {})
            else:
                self.assertNotEqual(dict(page.from_name.items()), {})
                self.assertNotEqual(dict(page.from_usage.items()), {})

            self.assertEqual(HUT[page_id], HUT[page_id << 16])

    def test_usage_page_names(self):
        self.assertEqual(sorted(self.pages.values()), sorted(HUT.usage_page_names))
        self.assertEqual(HUT.usage_page_names['Generic Desktop'], HUT.usage_pages[0x01])
        self.assertEqual(HUT['Generic Desktop'], HUT.usage_pages[0x01])

    def test_usage_gd(self):
        usages = {
            0x00: 'Undefined',
            0x01: 'Pointer',
            0x02: 'Mouse',
            0x03: 'Reserved',
            0x04: 'Joystick',
            0x05: 'Game Pad',
            0x06: 'Keyboard',
            0x07: 'Keypad',
            0x08: 'Multi Axis',
            0x09: 'Reserved',
            0x0A: 'Water Cooling Device / Assistive Control',
            0x0B: 'Computer Chassis Device',
            0x0C: 'Wireless Radio Controls',
            0x0D: 'Portable Device Control',
            0x0E: 'System Multi-Axis Controller',
            0x0F: 'Spatial Controller',
            0x30: 'X',
            0x31: 'Y',
            0x32: 'Z',
            0x33: 'Rx',
            0x34: 'Ry',
            0x35: 'Rz',
            0x36: 'Slider',
            0x37: 'Dial',
            0x38: 'Wheel',
            0x39: 'Hat switch',
            0x3A: 'Counted Buffer',
            0x3B: 'Byte Count',
            0x3C: 'Motion',
            0x3D: 'Start',
            0x3E: 'Select',
            0x3F: 'Reserved',
            0x40: 'Vx',
            0x41: 'Vy',
            0x42: 'Vz',
            0x43: 'Vbrx',
            0x44: 'Vbry',
            0x45: 'Vbrz',
            0x46: 'Vno',
            0x47: 'Feature',
            0x48: 'Resolution Multiplier',
            0x49: 'Qx',
            0x4A: 'Qy',
            0x4B: 'Qz',
            0x4C: 'Qw',
            0x80: 'System Control',
            0x81: 'System Power Down',
            0x82: 'System Sleep',
            0x83: 'System Wake Up',
            0x84: 'System Context Menu',
            0x85: 'System Main Menu',
            0x86: 'System App Menu',
            0x87: 'System Help Menu',
            0x88: 'System Menu Exit',
            0x89: 'System Menu Select',
            0x8A: 'System Menu Right',
            0x8B: 'System Menu Left',
            0x8C: 'System Menu Up',
            0x8D: 'System Menu Down',
            0x8E: 'System Cold Restart',
            0x8F: 'System Warm Restart',
            0x90: 'D-Pad Up',
            0x91: 'D-Pad Down',
            0x92: 'D-Pad Right',
            0x93: 'D-Pad Left',
            0x94: 'Index Trigger',
            0x95: 'Palm Trigger',
            0x96: 'Thumbstick',
            0xA0: 'System Dock',
            0xA1: 'System UnDock',
            0xA2: 'System Setup',
            0xA3: 'System Break',
            0xA4: 'System Debugger Break',
            0xA5: 'Application Break',
            0xA6: 'Application Debugger Break',
            0xA7: 'System Speaker Mute',
            0xA8: 'System Hibernate',
            0xB0: 'System Display Invert',
            0xB1: 'System Display Internal',
            0xB2: 'System Display External',
            0xB3: 'System Display Both',
            0xB4: 'System Display Dual',
            0xB5: 'System Display Toggle Internal External',
            0xB6: 'System Display Swap Primary Secondary',
            0xB7: 'System Display LCDAuto Scale',
            0xC0: 'Sensor Zone',
            0xC1: 'RPM',
            0xC2: 'Coolant Level',
            0xC3: 'Coolant Critical Level',
            0xC4: 'Coolant Pump',
            0xC5: 'Chassis Enclosure',
            0xC6: 'Wireless Radio Button',
            0xC7: 'Wireless Radio LED',
            0xC8: 'Wireless Radio Slider Switch',
            0xC9: 'System Display Rotation Lock Button',
            0xCA: 'System Display Rotation Lock Slider Switch',
            0xCB: 'Control Enable',
        }

        page = HUT[0x1]
        for u, uname in usages.items():
            if uname == 'Reserved':
                continue

            usage = page[u]
            self.assertEqual(usage.name, uname)
            self.assertEqual(usage.usage, u)
            self.assertEqual(page[u], page.from_name[uname])
            self.assertEqual(page[u], page.from_usage[u])

        for i in range(0xffff):
            if i not in usages or usages[i] == 'Reserved':
                self.assertNotIn(i, page)

    def test_32_bit_usage_lookup(self):
        self.assertEqual(HUT[0x1][0x1 << 16 | 0x31].name, 'Y')
        self.assertEqual(HUT[0x1][0x1 << 16 | 0x30].name, 'X')
        self.assertEqual(HUT[0x2][0x2 << 16 | 0x09].name, 'Airplane Simulation Device')
        self.assertEqual(HUT[0x2][0x2 << 16 | 0xB2].name, 'Anti-Torque Control')

        with self.assertRaises(KeyError):
            HUT[0x01][0x2 << 16 | 0x1]

    def test_duplicate_pages(self):
        # make sure we have no duplicate pages
        for p in HUT:
            page = HUT[p]
            if page == {} or page == {0: 'Undefined'}:
                continue

            keys = list(HUT)
            keys.remove(p)
            for k in keys:
                self.assertNotEqual(page, HUT[k])
