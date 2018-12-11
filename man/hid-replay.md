% HID-REPLAY(1)

NAME
----

hid-replay - HID input device replay through uhid

SYNOPSIS
--------
**hid-replay** \[\-\-verbose\] \[FILENAME\]

OPTIONS
-------

**\-\-verbose**
:     Enable debugging output


DESCRIPTION
-----------
**hid-replay** creates a virtual HID device based on the recorded file,
usually recorded by **hid-recorder(1)**. This device behaves as if it was
physically connected to the system. Any events in the recorded file are
replayed in realtime.

**hid-replay** is a low-level debugging tool. It uses the **uhid** kernel
model to create the device and all data is processed by the respective HID
kernel module for the device.

**hid-replay** needs to be able to write to _/dev/uhid_; usually this means it
must be run as root.


FILE FORMAT
----------
Files supported by **hid-replay** have the following syntax:

- **#** comment lines are ignored when parsing
- **D:** the device index, only used when recording multiple devices
- **R:** The report descriptor length in bytes, followed by the report
  descriptor bytes in hexadecimal
- **N:** the name of the device
- **P:** physical path
- **I:** bus vendor\_id product\_id
- **E:** timestamp size report in hexadecimal

CAUTION
-------
**hid-replay** is a very low level events injector. To have the virtual
device handled by the correct HID kernel module, **hid-replay** fakes that
the device is on the original bus (USB, I2C or BT). Thus, if the kernel
module in use has to write *back* to the device the kernel may oops if the
module is trying to directly talk to the physical layer.

Ensure to use this program with friendly HID modules that rely only on the
generic hid callbacks.

EXIT CODE
---------
**hid-replay** returns 1 on error.

SEE ALSO
--------
hid-recorder(1)

COPYRIGHT
---------
 Copyright 2012-2018, Benjamin Tissoires.

 Copyright 2018, Red Hat, Inc.

AUTHOR
------
 Benjamin Tissoires <benjamin.tissoires@redhat.com>
