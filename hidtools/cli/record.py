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

import argparse
import sys
import os

from hidtools.hidraw import HidrawDevice


def list_devices():
    outfile = sys.stdout if os.isatty(sys.stdout.fileno()) else sys.stderr
    devices = {}
    for fname in os.listdir('/dev/'):
        if not fname.startswith('hidraw'):
            continue

        with open(f'/dev/{fname}') as f:
            d = HidrawDevice(f)
            devices[int(fname[6:])] = d.name

    print('Available devices:', file=outfile)
    for num, name in sorted(devices.items()):
        print(f'/dev/hidraw{num}:	{name}', file=outfile)

    lo = min(devices.keys())
    hi = max(devices.keys())

    print(f'Select the device event number [{lo}-{hi}]: ',
          end='', flush=True, file=outfile)
    try:
        num = int(sys.stdin.readline())
        if num < lo or num > hi:
            raise ValueError
        return f'/dev/hidraw{num}'
    except ValueError:
        print('Invalid device', file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Record a HID device')
    parser.add_argument('device', metavar='/dev/hidrawX',
                        nargs="?", default=None,
                        type=argparse.FileType('r'),
                        help='Path to the hidraw device node')
    parser.add_argument('--output', metavar='output file',
                        nargs=1, default=sys.stdout,
                        type=argparse.FileType('w'),
                        help='The file to record to (default: stdout)')
    args = parser.parse_args()

    try:
        if args.device is None:
            args.device = open(list_devices())

        device = HidrawDevice(args.device)
        device.dump(args.output)

        while True:
            device.read_events()
            device.dump(args.output)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    if sys.version_info < (3, 6):
        sys.exit('Python 3.6 or later required')

    main()
