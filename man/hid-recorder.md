% HID-RECORDER(1)

NAME
----

hid-recorder - HID input device recorder

SYNOPSIS
--------
**hid-recorder** *\[\-\-output=output_file\]* *[/dev/hidrawX]* [*[/dev/hidrawX]* [...]]

OPTIONS
-------

**\-\-output=path/to/file**
:    Write the output to the given file. When omitted, **hid-recorder** prints to stdout.

DESCRIPTION
-----------
**hid-recorder** captures report descriptors and hid reports (events)
through the *hidraw* kernel module and prints them in a standardized format
(see below) to debug and replay HID devices.

When invoked without arguments, **hid-recorder** shows a list of available
devices.

**hid-recorder** needs to be able to read from the hidraw device; usually
this means it must be run as root.

FILE FORMAT
-----------

The output of **hid-recorder** has the following syntax:

- **#** comment lines are ignored when parsing
- **D:** the device index, only used when recording multiple devices
- **R:** The report descriptor length in bytes, followed by the report
  descriptor bytes in hexadecimal
- **N:** the name of the device
- **P:** physical path
- **I:** bus vendor\_id product\_id
- **E:** timestamp size report in hexadecimal


EXIT CODE
---------
**hid-recorder** returns 1 on error.

SEE ALSO
--------
hid-replay(1)

COPYRIGHT
---------
Copyright 2012-2018, Benjamin Tissoires.

Copyright 2018, Red Hat, Inc.

AUTHOR
------
 Benjamin Tissoires <benjamin.tissoires@redhat.com>
