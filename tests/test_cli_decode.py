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

import tempfile
import unittest
from tests.base import UHIDTestDevice
from hidtools.cli.decode import main as decode
import logging
logger = logging.getLogger('hidtools.test.cli.decode')


class BaseTest:
    class HidDecodeBase(unittest.TestCase):
        cli_args = []

        def run_hid_decode(self):
            with tempfile.NamedTemporaryFile(delete=True) as sourcefile:
                if isinstance(self.data, str):
                    data = bytes(self.data, encoding='utf-8')
                else:
                    data = self.data
                sourcefile.write(data)
                sourcefile.seek(0)
                with tempfile.NamedTemporaryFile(mode='r', delete=True) as outfile:
                    decode(['hid-decode.test'] + self.cli_args + [f'--output', outfile.name, sourcefile.name])
                    return outfile.readlines()

        @property
        def output(self):
            if not hasattr(self, '_output'):
                self._output = self.run_hid_decode()
            return self._output

        def output_to_bytes(self, output_lines):
            """Convert the hid-decode output into a list of bytes"""
            items = ', '.join(output_lines).split(', ')
            return [int(b, 16) for b in items if b.startswith('0x')]

        def test_read(self):
            self.assertIsNotNone(self.output)

        def test_basic_elements(self):
            all = '\n'.join(self.output)
            self.assertIn('Usage (', all)
            self.assertIn('Usage Page (', all)
            self.assertIn('Collection (Application)', all)
            self.assertIn('End Collection', all)

        def test_format(self):
            for line in self.output:
                if 'End Collection' in line:
                    self.assertRegex(line, '0xc0, *// +End Collection *[0-9]+\n')
                elif 'Push' in line:
                    self.assertRegex(line, '0xa4, *// +Push *[0-9]+\n')
                elif 'Pop' in line:
                    self.assertRegex(line, '0xb4, *// +Pop *[0-9]+\n')
                elif line == '**** win 8 certified ****\n':
                    pass
                else:
                    self.assertRegex(line, '0x[0-9a-f][0-9a-f], 0x[0-9a-f][0-9a-f], *// .*')


class TestHidRecording(BaseTest.HidDecodeBase):
    data = f'''
R: 67 05 01 09 02 a1 01 09 01 a1 00 05 09 19 01 29 10 15 00 25 01 95 10 75 01 81 02 05 01 16 01 80 26 ff 7f 75 10 95 02 09 30 09 31 81 06 15 81 25 7f 75 08 95 01 09 38 81 06 05 0c 0a 38 02 95 01 81 06 c0 c0
N: Logitech G500s Laser Gaming Mouse
I: 3 046d c24e
'''

    def test_dump(self):
        self.assertEqual(self.output[0].strip(), f'0x05, 0x01,                    // Usage Page (Generic Desktop)        0')
        self.assertEqual(self.output[1].strip(), f'0x09, 0x02,                    // Usage (Mouse)                       2')
        self.assertIn('End Collection', self.output[-1])
        self.assertIn('End Collection', self.output[-2])

        bytelist = self.output_to_bytes(self.output)
        strbytes = " ".join(f'{x:02x}' for x in bytelist)
        expected = f'R: {len(bytelist)} {strbytes}'
        self.assertEqual(self.data.split('\n')[1], expected)


class TestHidRecordingVerbose(TestHidRecording):
    cli_args = ['--verbose']


class TestBinDescriptor(BaseTest.HidDecodeBase):
    data = b'\x05\x01\t\x06\xa1\x01\x85\x01\x05\x07\x19\xe0)\xe7\x15\x00%\x01u\x01\x95\x08\x81\x02\x95\x05u\x08\x15\x00&\xa4\x00\x05\x07\x19\x00*\xa4\x00\x81\x00\xc0\x05\x0c\t\x01\xa1\x01\x85\x03u\x10\x95\x02\x15\x01&\x8c\x02\x19\x01*\x8c\x02\x81\x00\xc0\x06\x00\xff\t\x01\xa1\x01\x85\x10u\x08\x95\x06\x15\x00&\xff\x00\t\x01\x81\x00\t\x01\x91\x00\xc0\x06\x00\xff\t\x02\xa1\x01\x85\x11u\x08\x95\x13\x15\x00&\xff\x00\t\x02\x81\x00\t\x02\x91\x00\xc0'


class TestHidRecordingComments(BaseTest.HidDecodeBase):
    data = '''
# Logitech G500s Laser Gaming Mouse
# 0x05, 0x01,                    // Usage Page (Generic Desktop)        0
# 0x09, 0x02,                    // Usage (Mouse)                       2
# 0xa1, 0x01,                    // Collection (Application)            4
# 0x09, 0x01,                    //  Usage (Pointer)                    6
# 0xa1, 0x00,                    //  Collection (Physical)              8
# 0x05, 0x09,                    //   Usage Page (Button)               10
# 0x19, 0x01,                    //   Usage Minimum (1)                 12
# 0x29, 0x10,                    //   Usage Maximum (16)                14
# 0x15, 0x00,                    //   Logical Minimum (0)               16
# 0x25, 0x01,                    //   Logical Maximum (1)               18
# 0x95, 0x10,                    //   Report Count (16)                 20
# 0x75, 0x01,                    //   Report Size (1)                   22
# 0x81, 0x02,                    //   Input (Data,Var,Abs)              24
# 0x05, 0x01,                    //   Usage Page (Generic Desktop)      26
# 0x16, 0x01, 0x80,              //   Logical Minimum (-32767)          28
# 0x26, 0xff, 0x7f,              //   Logical Maximum (32767)           31
# 0x75, 0x10,                    //   Report Size (16)                  34
# 0x95, 0x02,                    //   Report Count (2)                  36
# 0x09, 0x30,                    //   Usage (X)                         38
# 0x09, 0x31,                    //   Usage (Y)                         40
# 0x81, 0x06,                    //   Input (Data,Var,Rel)              42
# 0x15, 0x81,                    //   Logical Minimum (-127)            44
# 0x25, 0x7f,                    //   Logical Maximum (127)             46
# 0x75, 0x08,                    //   Report Size (8)                   48
# 0x95, 0x01,                    //   Report Count (1)                  50
# 0x09, 0x38,                    //   Usage (Wheel)                     52
# 0x81, 0x06,                    //   Input (Data,Var,Rel)              54
# 0x05, 0x0c,                    //   Usage Page (Consumer Devices)     56
# 0x0a, 0x38, 0x02,              //   Usage (AC Pan)                    58
# 0x95, 0x01,                    //   Report Count (1)                  61
# 0x81, 0x06,                    //   Input (Data,Var,Rel)              63
# 0xc0,                          //  End Collection                     65
# 0xc0,                          // End Collection                      66
#
R: 67 05 01 09 02 a1 01 09 01 a1 00 05 09 19 01 29 10 15 00 25 01 95 10 75 01 81 02 05 01 16 01 80 26 ff 7f 75 10 95 02 09 30 09 31 81 06 15 81 25 7f 75 08 95 01 09 38 81 06 05 0c 0a 38 02 95 01 81 06 c0 c0
N: Logitech G500s Laser Gaming Mouse
I: 3 046d c24e
'''


class TestHidRecordingMultipleRDesc(BaseTest.HidDecodeBase):
    data = '''
R: 945 05 0d 09 04 a1 01 85 01 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 56 55 00 65 00 27 ff ff ff 7f 95 01 75 20 81 02 09 54 25 7f 95 01 75 08 81 02 85 0a 09 55 25 0a b1 02 85 44 06 00 ff 09 c5 15 00 26 ff 00 75 08 96 00 01 b1 02 c0 06 ff 01 09 01 a1 01 85 02 15 00 26 ff 00 75 08 95 40 09 00 81 02 c0 06 00 ff 09 01 a1 01 85 03 75 08 95 1f 09 01 91 02 c0 06 01 ff 09 01 a1 01 85 04 15 00 26 ff 00 75 08 95 13 09 00 81 02 c0
R: 945 05 0d 09 04 a1 01 85 01 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 56 55 00 65 00 27 ff ff ff 7f 95 01 75 20 81 02 09 54 25 7f 95 01 75 08 81 02 85 0a 09 55 25 0a b1 02 85 44 06 00 ff 09 c5 15 00 26 ff 00 75 08 96 00 01 b1 02 c0 06 ff 01 09 01 a1 01 85 02 15 00 26 ff 00 75 08 95 40 09 00 81 02 c0 06 00 ff 09 01 a1 01 85 03 75 08 95 1f 09 01 91 02 c0 06 01 ff 09 01 a1 01 85 04 15 00 26 ff 00 75 08 95 13 09 00 81 02 c0
'''


class TestHidrawSysfsReportDescriptor(BaseTest.HidDecodeBase):
    def setUp(self):
        self.rdesc = [
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
        self.uhid_device = UHIDTestDevice('hidraw test', 'Mouse', rdesc=self.rdesc)
        self.uhid_device.create_kernel_device()
        while not self.uhid_device.device_nodes:
            self.uhid_device.dispatch(10)

        node = self.uhid_device.device_nodes[0]
        self.assertTrue(node.startswith('/dev/input/'))
        node = node[len('/dev/input/'):]
        sysfs = f'/sys/class/input/{node}/device/device/report_descriptor'
        self.data = open(sysfs, 'rb').read()

    def tearDown(self):
        self.uhid_device.destroy()
        self.uhid_device.dispatch(10)

    def test_rdesc_match(self):
        # make sure the output matches our rdesc
        self.assertEqual(self.rdesc, self.output_to_bytes(self.output))

    def test_pass_hidraw(self):
        # same as above, but passes the hidraw node into hid-decode
        source = self.uhid_device.hidraw_nodes[0]
        with tempfile.NamedTemporaryFile(mode='r', delete=True) as outfile:
            decode(['hid-decode.test'] + self.cli_args + [f'--output', outfile.name, source])
            lines = outfile.readlines()
            self.assertEqual(self.rdesc, self.output_to_bytes(lines))

    def test_pass_event_node(self):
        # same as above, but passes the event node into hid-decode
        source = self.uhid_device.device_nodes[0]
        with tempfile.NamedTemporaryFile(mode='r', delete=True) as outfile:
            decode(['hid-decode.test'] + self.cli_args + [f'--output', outfile.name, source])
            lines = outfile.readlines()
            self.assertEqual(self.rdesc, self.output_to_bytes(lines))


if __name__ == "__main__":
    unittest.main()
