#!/bin/env python3
# -*- coding: utf-8 -*-
#
# Hid tools / parse_hid.py: generate a table of hid usages and definitions
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

import os
from parse import parse as _parse

DATA_DIRNAME = "data"
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, DATA_DIRNAME)


def parse_usages(usage_list):
    usages = {}
    idx, page_name = None, None
    for line in usage_list:
        line = line.strip()
        if not line:
            continue
        if line.startswith('('):
            r = _parse('({idx:x})\t{page_name}', line)
            assert(r is not None)
            idx = r['idx']
            page_name = r['page_name']
            continue

        r = _parse('{:x}-{:x}\t{name}', line)
        if r:
            if not 'reserved' in r['name'].lower():
                print(line)
            continue

        r = _parse('{usage:x}\t{name}', line)
        assert r is not None
        if 'reserved' in r['name'].lower():
            continue

        usages[r['usage']] = r['name']

    return idx, page_name, usages


def parse():
    usages = {}
    for filename in os.listdir(DATA_DIR):
        if filename.endswith('.hut'):
            with open(os.path.join(DATA_DIR, filename), 'r') as f:
                try:
                    idx, name, usages_list = parse_usages(f.readlines())
                    inv_usages_list = dict([(v, k) for k, v, in usages_list.items()])
                    usages[idx] = (name, filename, usages_list, inv_usages_list)
                except:
                    print(filename)
                    raise
    return usages
