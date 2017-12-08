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
import hid
from parse import parse as _parse


def get_report(time, report, rdesc):
    """
    Translate the given report to a human readable format.
    """

    output = f'{time:>10s} '
    indent_2nd_line = len(output)

    output += rdesc.get_str(report)

    # align the lines with the matching fields
    try:
        second_row = output.split('\n')[1]
    except IndexError:
        pass
    else:
        # we have a multi-line output, find where the fields are split
        colon = second_row.index(':')
        # the `1` / `-1` below is to remove the leading '|' that might match
        # with '/'
        indent_2nd_line = output.index(second_row[1:colon]) - 1

    indent = f'\n{" " * indent_2nd_line}'

    return indent.join(output.split('\n'))


def parse_event(line, rdesc_object):
    e, time, size, report = line.split(' ', 3)
    report = [int(item, 16) for item in report.split(' ')]
    assert int(size) == len(report)
    rdesc = rdesc_object.get(report[0], len(report))
    if rdesc is None:
        return None

    return get_report(time, report, rdesc)


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
            rdesc_object = hid.ReportDescriptor.parse_rdesc(line.lstrip("R: "))
            rdesc_object.dump(f_out)

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
