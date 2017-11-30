#!/bin/env python3
# -*- coding: utf-8 -*-
#
# Hid tools / parse_hid.py
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

import sys
import parse_rdesc
import hid
from parse import parse as _parse


def get_value(report, start, size, twos_comp):
    value = 0
    start_bit = start
    end_bit = start_bit + size
    data = report[int(start_bit / 8): int(end_bit / 8 + 1)]
    if len(data) == 0:
        return "<.>", end_bit
    for d in range(len(data)):
        value |= data[d] << (8 * d)

    bit_offset = start % 8
    value = value >> bit_offset
    garbage = (value >> size) << size
    value = value - garbage
    if twos_comp and size > 1:
        value = parse_rdesc.twos_comp(value, size)
    return value, end_bit


def get_report(time, report, rdesc, numbered):
    """
    Translate the given report to a human readable format.
    """
    total_bit_offset = 0

    output = f'{time:>10s} '
    sep = ''
    report_descriptor = rdesc
    if numbered:
        output += f'ReportID: {report[0]} '
        sep = '/'
        # first byte is report ID, actual data starts at 8
        total_bit_offset = 8
    prev = None
    usages_printed = {}
    indent_2nd_line = len(output)
    for report_item in report_descriptor:
        size = report_item.size
        array = not (report_item.type & (0x1 << 1))  # Variable
        const = report_item.type & (0x1 << 0)
        values = []
        usage_page_name = ''
        usage_page = report_item.usage_page >> 16
        if usage_page in hid.inv_usage_pages:
            usage_page_name = hid.inv_usage_pages[usage_page]

        # get the value and consumes bits
        for i in range(report_item.count):
            value, total_bit_offset = get_value(
                report, total_bit_offset, size, report_item.logical_min < 0)
            values.append(value)

        if const:
            output += f'{sep} # '
        elif not array:
            value_format = "{:d}"
            if size > 1:
                value_format = f'{{:{str(len(str(1 << size)) + 1)}d}}'
            if isinstance(values[0], str):
                value_format = "{}"
            usage = f' {report_item.usage_name}:'

            # if we don't get a key error this is a duplicate in
            # this report descriptor and we need a linebreak
            try:
                usages_printed[usage]
                usages_printed = {}
                output += '\n' + indent_2nd_line * ' '
            except KeyError:
                pass
            finally:
                usages_printed[usage] = True

            if (prev and
               prev.type == report_item.type and
               prev.usage == report_item.usage):
                sep = ","
                usage = ""
            output += f'{sep}{usage} {value_format.format(values[0])} '
        else:
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


def parse_event(line, rdesc_object):
    e, time, size, report = line.split(' ', 3)
    report = [int(item, 16) for item in report.split(' ')]
    rdesc, numbered = rdesc_object.get(report[0], int(size))
    if rdesc is not None:
        return get_report(time, report, rdesc, numbered)
    return None


def dump_report(line, rdesc_object, f_out):
    """
    Translate the given report to a human readable format.
    """
    event = parse_event(line, rdesc_object)
    if event:
        f_out.write(event)
        f_out.write("\n")


def parse_hid(f_in, f_out):
    rdesc_dict = {}
    d = 0
    while True:
        try:
            line = f_in.readline()
        except KeyboardInterrupt:
            break
        if line.startswith("R:"):
            rdesc_object = parse_rdesc.parse_rdesc(line.lstrip("R: "), f_out)
            rdesc_dict[d] = rdesc_object
            win8 = rdesc_object.win8
            if win8:
                f_out.write("**** win 8 certified ****\n")
        elif line.startswith("D:"):
            r = _parse('D:{d:d}', line)
            assert(r is not None)
            d = r['d']
        elif line.startswith("E:"):
            dump_report(line, rdesc_dict[d], f_out)
        elif line == '':
            # End of file
            break
        elif line.startswith("N:") or \
                line.startswith("P:") or \
                line.startswith("I:"):
            continue
        else:
            f_out.write(line)


def main():
    f = sys.stdin
    if len(sys.argv) > 1:
        f = open(sys.argv[1])
    parse_hid(f, sys.stdout)
    f.close()


if __name__ == "__main__":
    main()
