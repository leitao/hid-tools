% HID-DECODE(1)

NAME
----

hid-decode - HID input device report descriptor decoder

SYNOPSIS
--------
**hid-decode** *report-descriptor.bin*

**hid-decode** */dev/hidraw0*

**hid-decode** */dev/input/event0*

**hid-decode** *hid-recording*

DESCRIPTION
-----------
**hid-decode** decodes one or more HID report descriptors into into
human-readable format. It supports a variety of inputs:

- a binary format as exported in sysfs, e.g.
  _/sys/class/input/event0/device/device/report_descriptor_
- the format exported by **hid-recorder(1)**
- a _/dev/hidraw_ node
- a _/dev/input/event_ node

The format is deduced based on the input arguments. Undetected formats are
assumed to be binary files.

Accessing a _/dev/hidraw/_ node usually requires root permissions.

EXIT CODE
---------
**hid-decode** returns 1 on error.

SEE ALSO
--------
hid-recorder(1)

COPYRIGHT
---------
Copyright 2018, Red Hat, Inc.

AUTHOR
------
 Peter Hutterer <peter.hutterer@redhat.com>
