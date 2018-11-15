#!/bin/env python3
# -*- coding: utf-8 -*-
#
# Hid tools / parse_rdesc.py
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

import argparse
import sys
import hidtools.hid


def parse_rdesc(rdesc, output_type, dump_file):
    """
    Parse the given report descriptor and outputs it to stdout if show is True.
    Returns:
         - a ReportDescriptor object
    """

    rdesc_object = hidtools.hid.ReportDescriptor.from_bytes(rdesc)

    if dump_file:
        rdesc_object.dump(dump_file, type_output)

    return rdesc_object


def main():
    parser = argparse.ArgumentParser(description='Parse a HID recording and display the descriptor in a variety of formats')
    parser.add_argument('recording', nargs='?',
                        help='Path to device recording (stdin if missing)',
                        type=argparse.FileType('r'), default=sys.stdin)
    parser.add_argument('--output', metavar='output-file',
                        help='Path to output file (stdout if missing)',
                        nargs='?', type=argparse.FileType('w'), default=sys.stdout)
    parser.add_argument('--format', type=str, default='default',
                        choices=['default', 'kernel'],
                        help='Only display the HID descriptor')
    args = parser.parse_args()
    with args.recording as f:
        for line in f:
            if line.startswith("R:"):
                parse_rdesc(line.lstrip("R: "), args.format, args.output)
                break


if __name__ == "__main__":
    main()
