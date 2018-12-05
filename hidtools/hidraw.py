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

import array
import datetime
import fcntl
import os
import struct
import sys

def _ioctl(fd, EVIOC, code, return_type, buf = None):
	size = struct.calcsize(return_type)
	if buf == None:
		buf = size*'\x00'
	abs = fcntl.ioctl(fd, EVIOC(code, size), buf)
	return struct.unpack(return_type, abs)

# extracted from <asm-generic/ioctl.h>
_IOC_WRITE = 1
_IOC_READ = 2

_IOC_NRBITS = 8
_IOC_TYPEBITS = 8
_IOC_SIZEBITS = 14
_IOC_DIRBITS = 2

_IOC_NRSHIFT = 0
_IOC_TYPESHIFT = _IOC_NRSHIFT + _IOC_NRBITS
_IOC_SIZESHIFT = _IOC_TYPESHIFT + _IOC_TYPEBITS
_IOC_DIRSHIFT = _IOC_SIZESHIFT + _IOC_SIZEBITS

#define _IOC(dir,type,nr,size) \
#	(((dir)  << _IOC_DIRSHIFT) | \
#	 ((type) << _IOC_TYPESHIFT) | \
#	 ((nr)   << _IOC_NRSHIFT) | \
#	 ((size) << _IOC_SIZESHIFT))
def _IOC(dir, type, nr, size):
    return ( (dir << _IOC_DIRSHIFT) |
            (ord(type) << _IOC_TYPESHIFT) |
            (nr << _IOC_NRSHIFT) |
            (size << _IOC_SIZESHIFT))

    #define _IOR(type,nr,size)	_IOC(_IOC_READ,(type),(nr),(_IOC_TYPECHECK(size)))
def _IOR(type,nr,size):
    return _IOC(_IOC_READ, type, nr, size)

#define _IOW(type,nr,size)	_IOC(_IOC_WRITE,(type),(nr),(_IOC_TYPECHECK(size)))
def _IOW(type,nr,size):
    return _IOC(_IOC_WRITE, type, nr, size)


#define HIDIOCGRDESCSIZE	_IOR('H', 0x01, int)
def _IOC_HIDIOCGRDESCSIZE(none, len):
    return _IOR('H', 0x01, len)

def _HIDIOCGRDESCSIZE(fd):
    """ get report descriptors size """
    type = 'i'
    return int(*_ioctl(fd, _IOC_HIDIOCGRDESCSIZE, None, type))

#define HIDIOCGRDESC		_IOR('H', 0x02, struct hidraw_report_descriptor)
def _IOC_HIDIOCGRDESC(none, len):
    return _IOR('H', 0x02, len)

def _HIDIOCGRDESC(fd, size):
    """ get report descriptors """
    format = "I4096c"
    value = '\0'*4096
    tmp = struct.pack("i", size) + value[:4096].encode('utf-8').ljust(4096, b'\0')
    _buffer = array.array('B', tmp)
    fcntl.ioctl(fd, _IOC_HIDIOCGRDESC(None, struct.calcsize(format)), _buffer)
    size, = struct.unpack("i", _buffer[:4])
    value = _buffer[4:size+4]
    return size, value

#define HIDIOCGRAWINFO		_IOR('H', 0x03, struct hidraw_devinfo)
def _IOC_HIDIOCGRAWINFO(none, len):
    return _IOR('H', 0x03, len)

def _HIDIOCGRAWINFO(fd):
    """ get hidraw device infos """
    type = 'ihh'
    return _ioctl(fd, _IOC_HIDIOCGRAWINFO, None, type)

#define HIDIOCGRAWNAME(len)     _IOC(_IOC_READ, 'H', 0x04, len)
def _IOC_HIDIOCGRAWNAME(none, len):
    return _IOC(_IOC_READ, 'H', 0x04, len)

def _HIDIOCGRAWNAME(fd):
    """ get device name """
    type = 1024*'c'
    cstring = _ioctl(fd, _IOC_HIDIOCGRAWNAME, None, type)
    string = map(lambda x: x.decode('utf-8'), cstring)
    return "".join(string).rstrip('\x00')


class HidRawEvent(object):
    """
    A single event from a hidraw device. The first event always has a timestamp of 0.0,
    all other events are offset accordingly.

    .. attribute:: sec

        Timestamp seconds

    .. attribute:: usec

        Timestamp microseconds

    .. attribute:: bytes

        The data bytes read for this event
    """
    def __init__(self, sec, usec, bytes):
        self.sec, self.usec = sec, usec
        self.bytes = bytes

class HidRawDevice(object):
    """
    A hidraw device .

    :param File device: a file-like object pointing to ``/dev/hidrawX``

    .. attribute:: name

        The device name

    .. attribute:: bustype

        The numerical bus type (0x3 for USB, 0x5 for Bluetooth, see linux/input.h)

    .. attribute:: vendor_id

        16-bit numerical vendor ID

    .. attribute:: product_id

        16-bit numerical product ID
    
    .. attribute:: report_descriptor

        A list of 8-bit integers that is this device's report descriptor

    """
    def __init__(self, device):
        fd = device.fileno()
        self.device = device
        self.name = _HIDIOCGRAWNAME(fd)
        self.bustype, self.vendor_id, self.product_id = _HIDIOCGRAWINFO(fd)
        self.vendor_id &= 0xFFFF
        self.product_id &= 0xFFFF
        size = _HIDIOCGRDESCSIZE(fd)
        rsize, desc = _HIDIOCGRDESC(fd, size)
        assert rsize == size
        assert len(desc) == rsize
        self.report_descriptor = [x for x in desc]

        self.events = []

        self._dump_offset = 0
        self._time_offset = None

    def __repr__(self):
        return f'{self.name} bus: {self.bustype:02x} vendor: {self.vendor_id:04x} product: {self.product_id:04x}'


    def read_events(self):
        """
        Read events from the device and store them locally.

        This function simply calls ``os.read``, it is the caller's task to
        either make sure the device is set nonblocking or to handle any
        ``KeyboardInterrupt`` if this call does end up blocking.
        """
        data = os.read(self.device.fileno(), 4096)
        if not data:
            return None

        now = datetime.datetime.now()
        if self._time_offset is None:
            self._time_offset = now
        tdelta = now - self._time_offset
        bytes = struct.unpack('B'*len(data), data)

        self.events.append(HidRawEvent(tdelta.seconds, tdelta.microseconds, bytes))

        return len(data)

    def dump(self, file=sys.stdout, from_the_beginning=False):
        """
        Format this device in a file format in the form of ::

            R: 123 43 5 52 2 ... # the report descriptor size, followed by the integers
            N: the device name
            I: 3 124 abcd # bustype, vendor, product
            # comments are allowed
            E: 00001.000002 AB 12 34 56 # sec, usec, length, data
            ...

        This method is designed to be called repeatedly and only print the
        new events on each call. To repeat the dump from the beginning, set
        ``from_the_beginning`` to True.

        :param File file: the output file to write to
        :param bool from_the_beginning: if True, print everything again
             instead of continuing where we left off
        """

        if from_the_beginning:
            self._dump_offset = 0

        if self._dump_offset == 0:
            rd = " ".join([f'{b:02x}' for b in self.report_descriptor])
            sz = len(self.report_descriptor)
            print(f'R: {sz} {rd}', file=file)
            print(f'N: {self.name}', file=file)
            print(f'I: {self.bustype:x} {self.vendor_id:04x} {self.product_id:04x}', file=file, flush=True)

        for e in self.events[self._dump_offset:]:
            data = map(lambda x: f'{x:02x}', e.bytes)
            print(f'E: {e.sec:06d}.{e.usec:06d} {len(e.bytes)} {" ".join(data)}', flush=True)
        self._dump_offset = len(self.events)
