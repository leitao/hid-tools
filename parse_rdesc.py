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

import sys
import hid

type_output = "default"


def parse_rdesc(rdesc, dump_file=None):
    """
    Parse the given report descriptor and outputs it to stdout if show is True.
    Returns:
         - a ReportDescriptor object
    """

    rdesc_object = hid.ReportDescriptor.parse_rdesc(rdesc)

    if dump_file:
        rdesc_object.dump(dump_file, type_output)

    return rdesc_object


def main():
    f = open(sys.argv[1])
    if len(sys.argv) > 2:
        global type_output
        type_output = sys.argv[2]
    for line in f.readlines():
        if line.startswith("R:"):
            parse_rdesc(line.lstrip("R: "), sys.stdout)
            break
    f.close()


if __name__ == "__main__":
    main()
