#!/bin/env python3
# -*- coding: utf-8 -*-
#
# Hid tools / uhid.py
#
# Copyright (c) 2017 Benjamin Tissoires <benjamin.tissoires@gmail.com>
# Copyright (c) 2017 Red Hat, Inc.
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
import pyudev
import struct
import uuid


class UHIDUncompleteException(Exception):
    pass


class UHIDDevice(object):
    __UHID_LEGACY_CREATE = 0
    UHID_DESTROY = 1
    UHID_START = 2
    UHID_STOP = 3
    UHID_OPEN = 4
    UHID_CLOSE = 5
    UHID_OUTPUT = 6
    __UHID_LEGACY_OUTPUT_EV = 7
    __UHID_LEGACY_INPUT = 8
    UHID_GET_REPORT = 9
    UHID_GET_REPORT_REPLY = 10
    UHID_CREATE2 = 11
    UHID_INPUT2 = 12
    UHID_SET_REPORT = 13
    UHID_SET_REPORT_REPLY = 14

    def __init__(self):
        self._name = None
        self._phys = ''
        self._rdesc = None
        self._info = None
        self._fd = os.open('/dev/uhid', os.O_RDWR)
        self._set_report_fun = self._set_report
        self._get_report_fun = self._get_report
        self._output_report_fun = self._output_report
        self.opened = False
        self._udev = None
        self.uniq = f'uhid_{str(uuid.uuid4())}'

    @property
    def fd(self):
        return self._fd

    @property
    def rdesc(self):
        return self._rdesc

    @rdesc.setter
    def rdesc(self, rdesc):
        self._rdesc = rdesc

    @property
    def phys(self):
        return self._phys

    @phys.setter
    def phys(self, phys):
        self._phys = phys

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def info(self):
        return self._info

    @info.setter
    def info(self, info):
        self._info = info

    @property
    def bus(self):
        return self._info[0]

    @property
    def vid(self):
        return self._info[1]

    @property
    def pid(self):
        return self._info[2]

    @property
    def set_report(self):
        return self._set_report_fun

    @set_report.setter
    def set_report(self, set_report):
        self._set_report_fun = set_report

    def call_set_report(self, req, err):
        buf = struct.pack('< L L H',
                          UHIDDevice.UHID_SET_REPORT_REPLY,
                          req,
                          err)
        os.write(self._fd, buf)

    def _set_report(self, req, rnum, rtype, size, data):
        self.call_set_report(req, 1)

    @property
    def get_report(self):
        return self._get_report_fun

    @get_report.setter
    def get_report(self, get_report):
        self._get_report_fun = get_report

    def call_get_report(self, req, data, err):
        data = bytes(data)
        buf = struct.pack('< L L H H 4096s',
                          UHIDDevice.UHID_GET_REPORT_REPLY,
                          req,
                          err,
                          len(data),
                          data)
        os.write(self._fd, buf)

    def _get_report(self, req, rnum, rtype):
        self.call_get_report(req, [], 1)

    @property
    def output_report(self):
        return self._output_report_fun

    @output_report.setter
    def output_report(self, output_report):
        self._output_report_fun = output_report

    def _output_report(self, data, size, rtype):
        pass

    def call_input_event(self, data):
        data = bytes(data)
        buf = struct.pack('< L H 4096s',
                          UHIDDevice.UHID_INPUT2,
                          len(data),
                          data)
        os.write(self._fd, buf)

    @property
    def udev(self):
        if self._udev is None:
            context = pyudev.Context()
            for device in context.list_devices(subsystem='hid'):
                if self.uniq == device.properties['HID_UNIQ']:
                    self._udev = device
        return self._udev

    @property
    def sys_path(self):
        return self.udev.sys_path

    def create_kernel_device(self):
        if (self._name is None or
           self._rdesc is None or
           self._info is None):
            raise UHIDUncompleteException("missing uhid initialization")

        buf = struct.pack('< L 128s 64s 64s H H L L L L 4096s',
                          UHIDDevice.UHID_CREATE2,
                          bytes(self._name, 'utf-8'),  # name
                          bytes(self._phys, 'utf-8'),  # phys
                          bytes(self.uniq, 'utf-8'),  # uniq
                          len(self._rdesc),  # rd_size
                          self.bus,  # bus
                          self.vid,  # vendor
                          self.pid,  # product
                          0,  # version
                          0,  # country
                          bytes(self._rdesc))  # rd_data[HID_MAX_DESCRIPTOR_SIZE]

        n = os.write(self._fd, buf)
        assert n == len(buf)

    def destroy(self):
        buf = struct.pack('< L',
                          UHIDDevice.UHID_DESTROY)
        os.write(self._fd, buf)

    def process_one_event(self):
        buf = os.read(self._fd, 4380)
        assert len(buf) == 4380
        evtype = struct.unpack_from('< L', buf)[0]
        if evtype == UHIDDevice.UHID_START:
            ev, flags = struct.unpack_from('< L Q', buf)
        elif evtype == UHIDDevice.UHID_OPEN:
            self.opened = True
            print('open', self.sys_path)
        elif evtype == UHIDDevice.UHID_STOP:
            print('stop')
        elif evtype == UHIDDevice.UHID_CLOSE:
            self.opened = False
            print('close')
        elif evtype == UHIDDevice.UHID_SET_REPORT:
            ev, req, rnum, rtype, size, data = struct.unpack_from('< L L B B H 4096s', buf)
            self.set_report(req, rnum, rtype, size, data)
            print('set report', req, rtype, size, [f'{d:02x}' for d in data[:size]])
        elif evtype == UHIDDevice.UHID_GET_REPORT:
            ev, req, rnum, rtype = struct.unpack_from('< L L B B', buf)
            self.get_report(req, rnum, rtype)
            print('get report', req, rnum, rtype)
        elif evtype == UHIDDevice.UHID_OUTPUT:
            ev, data, size, rtype = struct.unpack_from('< L 4096s H B', buf)
            self.output_report(data, size, rtype)
            print('output', rtype, size, [f'{d:02x}' for d in data[:size]])
