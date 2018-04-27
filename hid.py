#!/bin/env python3
# -*- coding: utf-8 -*-
#
# Hid tools / hid.py: table of hid usages and definitions
#
# Copyright (c) 2012-2017 Benjamin Tissoires <benjamin.tissoires@gmail.com>
# Copyright (c) 2012-2017 Red Hat, Inc.
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

import copy
import parse_hut
from parse import parse as _parse


hid_items = {
    "Main": {
        "Input"			: 0b10000000,
        "Output"		: 0b10010000,
        "Feature"		: 0b10110000,
        "Collection"		: 0b10100000,
        "End Collection"	: 0b11000000,
    },

    "Global": {
        "Usage Page"		: 0b00000100,
        "Logical Minimum"	: 0b00010100,
        "Logical Maximum"	: 0b00100100,
        "Physical Minimum"	: 0b00110100,
        "Physical Maximum"	: 0b01000100,
        "Unit Exponent"		: 0b01010100,
        "Unit"			: 0b01100100,
        "Report Size"		: 0b01110100,
        "Report ID"		: 0b10000100,
        "Report Count"		: 0b10010100,
        "Push"			: 0b10100100,
        "Pop"			: 0b10110100,
    },

    "Local": {
        "Usage"			: 0b00001000,
        "Usage Minimum"		: 0b00011000,
        "Usage Maximum"		: 0b00101000,
        "Designator Index"	: 0b00111000,
        "Designator Minimum"	: 0b01001000,
        "Designator Maximum"	: 0b01011000,
        "String Index"		: 0b01111000,
        "String Minimum"	: 0b10001000,
        "String Maximum"	: 0b10011000,
        "Delimiter"		: 0b10101000,
    },
}

collections = {
    'PHYSICAL'			: 0,
    'APPLICATION'		: 1,
    'LOGICAL'			: 2,
}

sensor_mods = {
    0x00: 'Mod None',
    0x10: 'Mod Change Sensitivity Abs',
    0x20: 'Mod Max',
    0x30: 'Mod Min',
    0x40: 'Mod Accuracy',
    0x50: 'Mod Resolution',
    0x60: 'Mod Threshold High',
    0x70: 'Mod Threshold Low',
    0x80: 'Mod Calibration Offset',
    0x90: 'Mod Calibration Multiplier',
    0xa0: 'Mod Report Interval',
    0xb0: 'Mod Frequency Max',
    0xc0: 'Mod Period Max',
    0xd0: 'Mod Change Sensitivity Range Percent',
    0xe0: 'Mod Change Sensitivity Rel Percent',
    0xf0: 'Mod Vendor Reserved',
}

inv_hid = {}  # e.g 0b10000000 : "Input"
hid_type = {}  # e.g. "Input" : "Main"
for type, items in hid_items.items():
    for k, v in items.items():
        inv_hid[v] = k
        hid_type[k] = type

usages = parse_hut.parse()

usage_pages = {}
inv_usage_pages = {}
inv_usages = {}
for usage, (name, filename, usage_list, inv_usages_list) in usages.items():
    inv_usage_pages[usage] = name
    usage_pages[name] = usage
    for k, v in list(usage_list.items()):
        inv_usages[(usage << 16) | k] = v

inv_collections = dict([(v, k) for k, v in collections.items()])


def twos_comp(val, bits):
    """compute the 2's compliment of int value val"""
    if (val & (1 << (bits - 1))) != 0:
        val = val - (1 << bits)
    return val


def to_twos_comp(val, bits):
    return val & ((1 << bits) - 1)


class ParseError(Exception):
    pass


class HidRDescItem(object):

    def __init__(self, value):
        self.__parse(value)
        self.index_in_report = 0

    def __parse(self, value):
        self.r = r = value
        self.raw_value = []
        self.hid = r & 0xfc
        try:
            self.item = inv_hid[self.hid]
        except:
            error = f'error while parsing {value:02x}'
            if self.hid == 0:
                raise ParseError(error)
            else:
                raise KeyError(error)
        self.rsize = r & 0x3
        if self.rsize == 3:
            self.rsize = 4
        self.index = self.rsize
        self.value = 0

    def feed(self, value):
        "return True if the value was accepted by the item"
        if self.index <= 0:
            raise ParseError("this item is already full")
        self.raw_value.append(value)
        self.value |= value << (self.rsize - self.index) * 8
        self.index -= 1

        if self.index == 0:
            if self.item in ("Logical Minimum",
                             "Physical Minimum",
                             # "Logical Maximum",
                             # "Physical Maximum",
                             ):
                self.twos_comp()
            if self.item == "Unit Exponent" and self.value > 7:
                self.value -= 16

    def completed(self):
        # if index is null, then we have consumed all the incoming data
        return self.index == 0

    def twos_comp(self):
        if self.rsize:
            self.value = twos_comp(self.value, self.rsize * 8)
        return self.value

    def size(self):
        return 1 + len(self.raw_value)

    def __repr__(self):
        data = [f'{i:02x}' for i in self.raw_value]
        r = f'{self.r:02x}'
        if not len(data):
            return r
        return f'{r} {" ".join(data)}'

    def get_raw_values(self):
        data = str(self)
        # prefix each individual value by "0x" and insert "," in between
        data = f'0x{data.replace(" ", ", 0x")},'
        return data

    def get_human_descr(self, indent):
        item = self.item
        value = self.value
        up = self.usage_page
        descr = item
        if item in ("Report ID",
                    "Usage Minimum",
                    "Usage Maximum",
                    "Logical Minimum",
                    "Physical Minimum",
                    "Logical Maximum",
                    "Physical Maximum",
                    "Report Size",
                    "Report Count",
                    "Unit Exponent"):
            descr += f' ({str(value)})'
        elif item == "Collection":
            descr += f' ({inv_collections[value].capitalize()})'
            indent += 1
        elif item == "End Collection":
            indent -= 1
        elif item == "Usage Page":
            if value in inv_usage_pages:
                descr += f' ({inv_usage_pages[value]})'
            else:
                descr += f' (Vendor Usage Page 0x{value:02x})'
        elif item == "Usage":
            usage = value | up
            if usage in inv_usages:
                descr += f' ({inv_usages[usage]})'
            elif up == usage_pages['Sensor'] << 16:
                mod = (usage & 0xF000) >> 8
                usage &= ~0xF000
                mod_descr = sensor_mods[mod]
                try:
                    descr += f' ({inv_usages[usage]}  | {mod_descr})'
                except:
                    descr += f' (Unknown Usage 0x{value:02x})'
            else:
                descr += f' (Vendor Usage 0x{value:02x})'
        elif item == "Input" \
                or item == "Output" \
                or item == "Feature":
            descr += " ("
            if value & (0x1 << 0):
                descr += "Cnst,"
            else:
                descr += "Data,"
            if value & (0x1 << 1):
                descr += "Var,"
            else:
                descr += "Arr,"
            if value & (0x1 << 2):
                descr += "Rel"
            else:
                descr += "Abs"
            if value & (0x1 << 3):
                descr += ",Wrap"
            if value & (0x1 << 4):
                descr += ",NonLin"
            if value & (0x1 << 5):
                descr += ",NoPref"
            if value & (0x1 << 6):
                descr += ",Null"
            if value & (0x1 << 7):
                descr += ",Vol"
            if value & (0x1 << 8):
                descr += ",Buff"
            descr += ")"
        elif item == "Unit":
            systems = ("None", "SILinear", "SIRotation",
                       "EngLinear", "EngRotation")
            lengths = ("None", "Centimeter", "Radians", "Inch", "Degrees")
            masses = ("None", "Gram", "Gram", "Slug", "Slug")
            times = ("Seconds", "Seconds", "Seconds", "Seconds")
            temperatures = ("None", "Kelvin", "Kelvin", "Fahrenheit", "Fahrenheit")
            currents = ("Ampere", "Ampere", "Ampere", "Ampere")
            luminous_intensisties = ("Candela", "Candela", "Candela", "Candela")
            units = (lengths, masses, times, temperatures,
                     currents, luminous_intensisties)

            system = value & 0xf

            descr += " ("
            for i in range(len(units), 0, -1):
                v = (value >> i * 4) & 0xf
                v = twos_comp(v, 4)
                if v:
                    descr += units[i - 1][system]
                    if v != 1:
                        descr += '^' + str(v)
                    descr += ","
            descr += systems[system] + ')'
        elif item == "Push":
            pass
        elif item == "Pop":
            pass
        eff_indent = indent
        if item == "Collection":
            eff_indent -= 1
        return ' ' * eff_indent + descr, indent

    @classmethod
    def from_human_descr(cls, line, usage_page):
        data = None
        if '(' in line:
            r = _parse('{ws:s}{name} ({data})', line)
            assert(r is not None)
            name = r['name']
            data = r['data']
            if data.lower().startswith('0x'):
                try:
                    data = int(data[2:], 16)
                except ValueError:
                    pass
            else:
                try:
                    data = int(data)
                except ValueError:
                    pass
        else:
            name = line.strip()

        value = None

        if isinstance(data, str):
            if name == "Usage Page":
                value = usage_pages[data]
                usage_page = value
            elif name == "Usage":
                value = usages[usage_page][3][data]
            elif name == "Collection":
                value = collections[data.upper()]
            elif name in 'Input Output Feature':
                value = 0
                possible_types = (
                    'Cnst',
                    'Var',
                    'Rel',
                    'Wrap',
                    'NonLin',
                    'NoPref',
                    'Null',
                    'Vol',
                    'Buff',
                )
                for i, v in enumerate(possible_types):
                    if v in data:
                        value |= (0x1 << i)
            elif name == 'Unit':
                systems = ("None", "SILinear", "SIRotation", "EngLinear", "EngRotation")
                lengths = ("None", "Centimeter", "Radians", "Inch", "Degrees")
                masses = ("None", "Gram", "Gram", "Slug", "Slug")
                times = ("Seconds", "Seconds", "Seconds", "Seconds")
                temperatures = ("None", "Kelvin", "Kelvin", "Fahrenheit", "Fahrenheit")
                currents = ("Ampere", "Ampere", "Ampere", "Ampere")
                luminous_intensisties = ("Candela", "Candela", "Candela", "Candela")
                units = (lengths, masses, times, temperatures,
                         currents, luminous_intensisties)

                r = None
                if '^' in data:
                    r = _parse('{unit}^{exp:d},{system}', data)
                    assert(r is not None)
                else:
                    r = _parse('{unit},{system}', data)
                    assert(r is not None)
                unit = r['unit']
                try:
                    exp = r['exp']
                except KeyError:
                    exp = 1
                system = r['system']

                system = systems.index(system)

                for i, u in enumerate(units):
                    if unit in u:
                        unit = i + 1
                        break

                unit_value = to_twos_comp(exp, 4)
                unit_value <<= unit * 4

                value = unit_value | system
        else:  # data has been converted to an int already
            if name == "Usage Page":
                usage_page = data
            value = data

        size = 0
        bit_size = 0
        if value is not None:
            bit_size = len(f'{value + 1:x}') * 4
        else:
            value = 0
        tag = hid_items[hid_type[name]][name]
        size = 0
        v_count = 0
        if bit_size == 0:
            pass
        elif bit_size <= 8:
            size = 1
            v_count = 1
        elif bit_size <= 16:
            size = 2
            v_count = 2
        else:
            size = 3
            v_count = 4

        if name == "Unit Exponent" and value < 0:
            value += 16
            value = to_twos_comp(value, v_count * 8)

        item = HidRDescItem(tag | size)
        item.usage_page = usage_page << 16

        for i in range(v_count):
            item.feed((value >> (i * 8)) & 0xff)

        return item

    def dump_rdesc_kernel(self, indent, dump_file):
        """
        Format the hid item in a C-style format.
        """
        # offset = self.index_in_report
        line = self.get_raw_values()
        line += "\t" * (int((40 - len(line)) / 8))

        descr, indent = self.get_human_descr(indent)

        descr += "\t" * (int((52 - len(descr)) / 8))
        # dump_file.write(f'{line}/* {descr} {str(offset)} */\n')
        dump_file.write(f'\t{line}/* {descr}*/\n')
        return indent

    def dump_rdesc_array(self, indent, dump_file):
        """
        Format the hid item in a C-style format.
        """
        offset = self.index_in_report
        line = self.get_raw_values()
        line += " " * (30 - len(line))

        descr, indent = self.get_human_descr(indent)

        descr += " " * (35 - len(descr))
        dump_file.write(f'{line} // {descr} {str(offset)}\n')
        return indent

    def dump_rdesc_lsusb(self, indent, dump_file):
        """
        Format the hid item in a lsusb -v format.
        """
        item = self.item()
        up = self.usage_page
        value = self.value
        data = "none"
        if item != "End Collection":
            data = " ["
            for v in self.raw_value:
                data += f' 0x{v & 0xff:02x}'
            data += f' ] {value}'
        dump_file.write(f'            Item({hid_type[item]:6s}): {item}, data={data}\n')
        if item == "Usage":
            usage = up | value
            if usage in list(inv_usages.keys()):
                dump_file.write(f'                 {inv_usages[usage]}\n')


class HidField(object):

    def __init__(self,
                 report_ID,
                 logical,
                 physical,
                 application,
                 collection,
                 value,
                 usage_page,
                 usage,
                 logical_min,
                 logical_max,
                 item_size,
                 count):
        self.report_ID = report_ID
        self.logical = logical
        self.physical = physical
        self.application = application
        self.collection = collection
        self.type = value
        self.usage_page = usage_page
        self.usage = usage
        self.usages = None
        self.logical_min = logical_min
        self.logical_max = logical_max
        self.size = item_size
        self.count = count

    def copy(self):
        c = copy.copy(self)
        if self.usages is not None:
            c.usages = self.usages[:]
        return c

    def _usage_name(self, usage):
        usage_page = usage >> 16
        if usage_page in inv_usage_pages and \
                inv_usage_pages[usage_page] == "Button":
            usage = f'B{str(usage & 0xFF)}'
        elif usage in inv_usages:
            usage = inv_usages[usage]
        else:
            usage = f'0x{usage:04x}'
        return usage

    @property
    def usage_name(self):
        return self._usage_name(self.usage)

    def get_usage_name(self, index):
        return self._usage_name(self.usages[index])

    @property
    def physical_name(self):
        phys = self.physical
        if self.physical in inv_usages:
            phys = inv_usages[self.physical]
        else:
            try:
                phys = f'0x{phys:04x}'
            except:
                pass
        return phys

    def _get_value(self, report, idx):
        value = 0
        start_bit = self.start + self.size * idx
        end_bit = start_bit + self.size * (idx + 1)
        data = report[int(start_bit / 8): int(end_bit / 8 + 1)]
        if len(data) == 0:
            return ["<.>"]
        for d in range(len(data)):
            value |= data[d] << (8 * d)

        bit_offset = start_bit % 8
        value = value >> bit_offset
        garbage = (value >> self.size) << self.size
        value = value - garbage
        if self.logical_min < 0 and self.size > 1:
            value = twos_comp(value, self.size)
        return value

    def get_values(self, report):
        return [self._get_value(report, i) for i in range(self.count)]

    def _set_value(self, report, value, idx):
        start_bit = self.start + self.size * idx
        n = self.size

        max = (1 << n) - 1
        if value > max:
            raise Exception(f'_set_value() called with too large value {value} for size {self.size}')

        byte_idx = int(start_bit / 8)
        bit_shift = start_bit % 8
        bits_to_set = 8 - bit_shift

        while n - bits_to_set >= 0:
            report[byte_idx] &= ~(0xff << bit_shift)
            report[byte_idx] |= (value << bit_shift) & 0xff
            value >>= bits_to_set
            n -= bits_to_set
            bits_to_set = 8
            bit_shift = 0
            byte_idx += 1

        # last nibble
        if n:
            bit_mask = (1 << n) - 1
            report[byte_idx] &= ~(bit_mask << bit_shift)
            report[byte_idx] |= value << bit_shift

    def set_values(self, report, data):
        if len(data) != self.count:
            raise Exception("-EINVAL")

        for idx in range(self.count):
            v = data[idx]
            if self.logical_min < 0:
                v = to_twos_comp(v, self.size)
            self._set_value(report, v, idx)

    @property
    def array(self):
        return not (self.type & (0x1 << 1))  # Variable

    @property
    def const(self):
        return self.type & (0x1 << 0)

    @property
    def usage_page_name(self):
        usage_page_name = ''
        usage_page = self.usage_page >> 16
        if usage_page in inv_usage_pages:
            usage_page_name = inv_usage_pages[usage_page]
        return usage_page_name

    @classmethod
    def getHidFields(cls,
                     report_ID,
                     logical,
                     physical,
                     application,
                     collection,
                     value,
                     usage_page,
                     usages,
                     usage_min,
                     usage_max,
                     logical_min,
                     logical_max,
                     item_size,
                     count):
        usage = usage_min
        if len(usages) > 0:
            usage = usages[0]

        item = cls(report_ID,
                   logical,
                   physical,
                   application,
                   collection,
                   value,
                   usage_page,
                   usage,
                   logical_min,
                   logical_max,
                   item_size,
                   1)
        items = []

        if value & (0x1 << 0):  # Const item
            item.size *= count
            return [item]
        elif value & (0x1 << 1):  # Variable item
            if usage_min and usage_max:
                usage = usage_min
                for i in range(count):
                    item = item.copy()
                    item.usage = usage
                    items.append(item)
                    if usage < usage_max:
                        usage += 1
            else:
                for i in range(count):
                    if i < len(usages):
                        usage = usages[i]
                    else:
                        usage = usages[-1]
                    item = item.copy()
                    item.usage = usage
                    items.append(item)
        else:  # Array item
            if usage_min and usage_max:
                usages = list(range(usage_min, usage_max + 1))
            item.usages = usages
            item.count = count
            return [item]
        return items


class HidReport(object):
    def __init__(self, report_ID, application):
        self.fields = []
        self.report_ID = report_ID
        self.application = application
        self._application_name = None
        self._bitsize = 0
        if self.numbered:
            self._bitsize = 8

    def append(self, field):
        self.fields.append(field)
        field.start = self._bitsize
        self._bitsize += field.size

    def extend(self, fields):
        self.fields.extend(fields)
        for f in fields:
            f.start = self._bitsize
            self._bitsize += f.size

    @property
    def application_name(self):
        try:
            return inv_usages[self.application]
        except KeyError:
            return 'Vendor'

    @property
    def numbered(self):
        return self.report_ID >= 0

    @property
    def bitsize(self):
        return self._bitsize

    @property
    def size(self):
        return self._bitsize >> 3

    @property
    def has_been_populated(self):
        if self.report_ID >= 0:
            return self.bitsize > 8
        return self.size > 0

    def __iter__(self):
        return iter(self.fields)

    def _fix_xy_usage_for_mt_devices(self, usage):
        if usage not in self.prev_seen_usages:
            return usage

        # multitouch devices might have 2 X for CX, TX
        if usage == 'X' and ('Y' not in self.prev_seen_usages or
                             'CY' in self.prev_seen_usages):
            usage = 'CX'

        # multitouch devices might have 2 Y for CY, TY
        if usage == 'Y' and ('X' not in self.prev_seen_usages or
                             'CX' in self.prev_seen_usages):
            usage = 'CY'

        return usage

    def _format_one_event(self, data, global_data, hidInputItem, r):
        if hidInputItem.const:
            return

        # FIXME: arrays?
        usage = hidInputItem.usage_name

        usage = self._fix_xy_usage_for_mt_devices(usage)

        if (self.prev_collection is not None and
           self.prev_collection != hidInputItem.collection and
           usage in self.prev_seen_usages):
            if len(data) > 0:
                data.pop(0)
            self.prev_seen_usages.clear()

        value = 0
        field = usage.replace(' ', '').lower()
        if len(data) > 0 and hasattr(data[0], field):
            value = getattr(data[0], field)
        elif hasattr(global_data, field):
            value = getattr(global_data, field)

        hidInputItem.set_values(r, [value])
        self.prev_collection = hidInputItem.collection
        self.prev_seen_usages.append(usage)

    def format_report(self, data, global_data):
        self.prev_seen_usages = []
        self.prev_collection = None
        r = [0 for i in range(self.size)]

        if self.numbered:
            r[0] = self.report_ID

        for item in self:
            self._format_one_event(data, global_data, item, r)

        if len(data) > 0:
            # remove the last item we just processed
            data.pop(0)

        return r

    def get_str(self, data, split_lines=True):
        """
        Translate the given report to a human readable format.
        """

        output = ''

        self.prev_seen_usages = []
        self.prev_collection = None
        sep = ''
        if self.numbered:
            assert self.report_ID == data[0]
            output += f'ReportID: {self.report_ID} '
            sep = '/'
        prev = None
        for report_item in self:
            if report_item.const:
                output += f'{sep} # '
                continue

            # get the value and consumes bits
            values = report_item.get_values(data)

            if not report_item.array:
                value_format = "{:d}"
                if report_item.size > 1:
                    value_format = f'{{:{str(len(str(1 << report_item.size)) + 1)}d}}'
                if isinstance(values[0], str):
                    value_format = "{}"
                usage_name = self._fix_xy_usage_for_mt_devices(report_item.usage_name)
                usage = f' {usage_name}:'

                # if we don't get a key error this is a duplicate in
                # this report descriptor and we need a linebreak
                if (split_lines and
                   self.prev_collection is not None and
                   self.prev_collection != report_item.collection):
                    self.prev_seen_usages = []
                    output += '\n'
                self.prev_collection = report_item.collection
                self.prev_seen_usages.append(usage_name)

                # do not reapeat the usage name if several are in a row
                if (prev and
                   prev.type == report_item.type and
                   prev.usage == report_item.usage):
                    sep = ","
                    usage = ""
                output += f'{sep}{usage} {value_format.format(values[0])} '
            else:
                usage_page_name = report_item.usage_page_name
                if not usage_page_name:
                    usage_page_name = "Array"
                usages = []
                for v in values:
                    if (v < report_item.logical_min or
                       v > report_item.logical_max):
                        usages.append('')
                    else:
                        usage = ""
                        if isinstance(values[0], str):
                            usage = v
                        else:
                            usage = f'{v:02x}'
                        if ('vendor' not in usage_page_name.lower() and
                           v > 0 and
                           v < len(report_item.usages)):
                            usage = report_item.get_usage_name(v)
                            if "no event indicated" in usage.lower():
                                usage = ''
                        usages.append(usage)
                output += f'{sep}{usage_page_name} [{", ".join(usages)}] '
            sep = '|'
            prev = report_item
        return output


class ReportDescriptor(object):
    class Globals(object):
        def __init__(self, other=None):
            self.usage_page = 0
            self.logical = None
            self.physical = None
            self.application = None
            self.logical_min = 0
            self.logical_max = 0
            self.count = 0
            self.item_size = 0
            if other is not None:
                self.usage_page = other.usage_page
                self.logical = other.logical
                self.physical = other.physical
                self.application = other.application
                self.logical_min = other.logical_min
                self.logical_max = other.logical_max
                self.count = other.count
                self.item_size = other.item_size

    def __init__(self):
        self.input_reports = {}
        self.feature_reports = {}
        self.output_reports = {}
        self.index = 1  # 0 is the size
        self.glob = ReportDescriptor.Globals()
        self.global_stack = []
        self.usages = []
        self.usage_min = 0
        self.usage_max = 0
        self.collection = [0, 0, 0] # application, physical, logical
        self.current_report = {}
        self.report_ID = -1
        self.win8 = False
        self.rdesc_items = []
        self.rdesc_size = 0
        self.current_item = None

    def append(self, item):
        self.rdesc_items.append(item)
        item.index_in_report = self.rdesc_size
        self.rdesc_size += item.size()

    def consume(self, value):
        """ item is an int8 """
        if not self.current_item:
            # initial state
            self.current_item = HidRDescItem(value)
        else:
            # try to feed the value to the current item
            self.current_item.feed(value)
        if self.current_item.completed():
            rdesc_item = self.current_item
            self.append(rdesc_item)

            self.parse_item(rdesc_item)
            self.current_item = None

            return rdesc_item
        return None

    def get(self, reportID, reportSize):
        try:
            report = self.input_reports[reportID]
        except KeyError:
            try:
                report = self.input_reports[-1]
            except KeyError:
                return None

        # if the report is larger than it should, it's OK
        if report.size >= reportSize:
            return report

        return None

    def get_report_from_application(self, application):
        for r in self.input_reports.values():
            if r.application == application or r.application_name == application:
                return r
        return None

    def _get_current_report(self, type):
        report_lists = {
            'Input': self.input_reports,
            'Output': self.output_reports,
            'Feature': self.feature_reports,
        }

        try:
            cur = self.current_report[type]
        except KeyError:
            cur = None

        if cur is not None and cur.report_ID != self.report_ID:
            cur = None

        if cur is None:
            try:
                cur = report_lists[type][self.report_ID]
            except KeyError:
                cur = HidReport(self.report_ID, self.glob.application)
                report_lists[type][self.report_ID] = cur
        return cur

    def parse_item(self, rdesc_item):
        # store current usage_page in rdesc_item
        rdesc_item.usage_page = self.glob.usage_page
        item = rdesc_item.item
        value = rdesc_item.value

        if item == "Report ID":
            self.report_ID = value
        elif item == "Push":
            self.global_stack.append(self.glob)
            self.glob = ReportDescriptor.Globals(self.glob)
        elif item == "Pop":
            self.glob = self.global_stack.pop()
        elif item == "Usage Page":
            self.glob.usage_page = value << 16
            # reset the usage list
            self.usages = []
            self.usage_min = 0
            self.usage_max = 0
        elif item == "Collection":
            c = inv_collections[value]
            try:
                if c == 'PHYSICAL':
                    self.collection[1] += 1
                    self.glob.physical = self.usages[-1]
                elif c == 'APPLICATION':
                    self.collection[0] += 1
                    self.glob.application = self.usages[-1]
                else:  # 'LOGICAL'
                    self.collection[2] += 1
                    self.glob.logical = self.usages[-1]
            except IndexError:
                pass
            # reset the usage list
            self.usages = []
            self.usage_min = 0
            self.usage_max = 0
        elif item == "Usage Minimum":
            self.usage_min = value | self.glob.usage_page
        elif item == "Usage Maximum":
            self.usage_max = value | self.glob.usage_page
        elif item == "Logical Minimum":
            self.glob.logical_min = value
        elif item == "Logical Maximum":
            self.glob.logical_max = value
        elif item == "Usage":
            self.usages.append(value | self.glob.usage_page)
        elif item == "Report Count":
            self.glob.count = value
        elif item == "Report Size":
            self.glob.item_size = value
        elif item in ("Input", "Feature", "Output"):
            self.current_input_report = self._get_current_report(item)

            inputItems = HidField.getHidFields(self.report_ID,
                                               self.glob.logical,
                                               self.glob.physical,
                                               self.glob.application,
                                               tuple(self.collection),
                                               value,
                                               self.glob.usage_page,
                                               self.usages,
                                               self.usage_min,
                                               self.usage_max,
                                               self.glob.logical_min,
                                               self.glob.logical_max,
                                               self.glob.item_size,
                                               self.glob.count)
            self.current_input_report.extend(inputItems)
            if item == "Feature" and len(self.usages) > 0 and self.usages[-1] == 0xff0000c5:
                self.win8 = True
            self.usages = []
            self.usage_min = 0
            self.usage_max = 0

    def dump(self, dump_file, type_output='default'):
        indent = 0
        for rdesc_item in self.rdesc_items:
            if type_output == "default":
                indent = rdesc_item.dump_rdesc_array(indent, dump_file)
            else:
                indent = rdesc_item.dump_rdesc_kernel(indent, dump_file)

    def dump_raw(self, dumpfile):
        dumpfile.write(self.data_txt())

    def size(self):
        size = 0
        for rdesc_item in self.rdesc_items:
            size += rdesc_item.size()
        return size

    def data(self):
        string = self.data_txt()
        data = [int(i, 16) for i in string.split()]
        return data

    def data_txt(self):
        return " ".join([str(i) for i in self.rdesc_items])

    @classmethod
    def parse_rdesc(cls, rdesc):
        """
        Parse the given report descriptor.
        Returns:
         - a ReportDescriptor object
        """

        if isinstance(rdesc, str):
            rdesc = [int(r, 16) for r in rdesc.split()[1:]]

        rdesc_object = ReportDescriptor()
        for i, v in enumerate(rdesc):
            if i == len(rdesc) - 1 and v == 0:
                # some device present a trailing 0, skipping it
                break
            rdesc_object.consume(v)

        return rdesc_object

    @classmethod
    def from_rdesc_str(cls, rdesc_str):
        usage_page = 0
        rdesc_object = ReportDescriptor()
        for line in rdesc_str.splitlines():
            if line.strip() == '':
                continue
            item = HidRDescItem.from_human_descr(line, usage_page)
            usage_page = item.usage_page >> 16
            rdesc_object.append(item)
            rdesc_object.parse_item(item)

        return rdesc_object

    def format_report(self, data, global_data=None, reportID=None, application=None):
        # make sure the data is iterable
        try:
            iter(data)
        except TypeError:
            data = [data]

        rdesc = None

        if application is not None:
            rdesc = self.get_report_from_application(application)
        else:
            if reportID is None:
                reportID = -1
            rdesc = self.input_reports[reportID]

        return rdesc.format_report(data, global_data)

    def get_str(self, data, split_lines=True):
        rdesc = self.get(data[0], len(data))
        if rdesc is None:
            return None

        return rdesc.get_str(data, split_lines)
