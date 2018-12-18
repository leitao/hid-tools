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
import os
import re
import sys
import hidtools.hid
import hidtools.hidraw
import logging
logging.basicConfig(format='%(levelname)s: %(name)s: %(message)s',
                    level=logging.INFO)
base_logger = logging.getLogger('hid')
logger = logging.getLogger('hid.decode')


class Oops(Exception):
    pass


def open_sysfs_rdesc(path):
    logger.debug(f'Reading sysfs file {path}')
    with open(path, 'rb') as fd:
        data = fd.read()
        return [hidtools.hid.ReportDescriptor.from_bytes(data)]


def open_devnode_rdesc(path):
    if not path.startswith('/dev/input/event'):
        raise Oops(f'Unexpected event node: {path}')

    node = path[len('/dev/input/'):]
    # should use pyudev here, but let's keep that for later
    sysfs = f'/sys/class/input/{node}/device/device/report_descriptor'

    if not os.path.exists(sysfs):
        raise Oops(f'Unable to find report descriptor for {path}, is this a HID device?')

    return open_sysfs_rdesc(sysfs)


def open_hidraw(path):
    with open(path, 'rb+') as fd:
        device = hidtools.hidraw.HidrawDevice(fd)
        return [device.report_descriptor]


def open_binary(path):
    # This will misidentify a few files (e.g. UTF-16) as binary but for the
    # inputs we need to accept it doesn't matter
    with open(path, 'rb') as fd:
        data = fd.read(4096)
        if b'\0' in data:
            logger.debug(f'{path} is a binary file')
            return [hidtools.hid.ReportDescriptor.from_bytes(data)]
    return None


def interpret_file_hidrecorder(lines):
    r_lines = [l for l in lines if l.startswith('R: ')]
    if not r_lines:
        return None

    rdescs = []
    for l in r_lines:
        bytes = l[3:]  # drop R:
        rdescs.append(hidtools.hid.ReportDescriptor.from_string(bytes))

    return rdescs


def open_report_descriptor(path):
    abspath = os.path.abspath(path)
    logger.debug(f'Processing {abspath}')

    if os.path.isdir(abspath) or not os.path.exists(abspath):
        raise Oops(f'Invalid path: {path}')

    if re.match('/sys/.*/report_descriptor', abspath):
        return open_sysfs_rdesc(path)
    if re.match('/dev/input/event[0-9]+', abspath):
        return open_devnode_rdesc(path)
    if re.match('/dev/hidraw[0-9]+', abspath):
        return open_hidraw(path)
    rdesc = open_binary(path)
    if rdesc is not None:
        return rdesc

    with open(path, 'r') as fd:
        logger.debug(f'Opening {path} as text file')
        lines = fd.readlines()
        rdesc = interpret_file_hidrecorder(lines)
        if rdesc is not None:
            return rdesc

    raise Oops(f'Unable to detect file type for {path}')


def main(argv=sys.argv):
    try:
        parser = argparse.ArgumentParser(description='Decode a HID report descriptor to human-readable format ')
        parser.add_argument('report_descriptor', help='Path to report descriptor(s)', nargs='+', type=str)
        parser.add_argument('--output', metavar='output-file',
                            nargs=1, default=[sys.stdout],
                            type=argparse.FileType('w'),
                            help='The file to record to (default: stdout)')
        parser.add_argument('--verbose', action='store_true',
                            default=False, help='Show debugging information')
        args = parser.parse_args(argv[1:])
        # argparse gives us a list size 1 for nargs 1
        output = args.output[0]
        if args.verbose:
            base_logger.setLevel(logging.DEBUG)
        for path in args.report_descriptor:
            rdescs = open_report_descriptor(path)
            for rdesc in rdescs:
                rdesc.dump(output)
                if rdesc.win8:
                    output.write("**** win 8 certified ****\n")
    except BrokenPipeError:
        pass
    except PermissionError as e:
        print(f'{e}', file=sys.stderr)
    except Oops as e:
        print(f'{e}', file=sys.stderr)


if __name__ == "__main__":
    main()
