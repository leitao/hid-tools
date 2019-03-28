hid-tools is a set of tools to interact with the kernel's HID subsystem.

It can be run directly from the git repository or installed via `pip3
install hid-tools`.

# Installation

The `hid-tools` repository does not need to be installed, all tools and
kernel tests can be run straight from the git repository. Where the tools
need to be installed, it is recommended to use `pip`:

```
$ pip3 install --user .
```

This installs all tools into the user-specifc Python paths. Skip the
`--user` flag where it needs to be installed system-wide. Removal of the
tools works with `pip` as well:

```
$ pip3 uninstall hid-tools
```

# Debugging tools for users

## hid-recorder

`hid-recorder` prints the HID Report Descriptor from a `/dev/hidraw` device
node and any HID reports coming from that device. The output format can be
used with `hid-replay` for debugging. When run without any arguments, the
tool prints a list of available devices.

```
$ sudo hid-recorder
```

## hid-replay

`hid-replay` takes the output from `hid-recorder` and replays it through a
virtual HID device that looks exactly like the one recorded.

```
$ sudo hid-replay recording-file.hid
```

## hid-decode

`hid-decode` takes a HID Report Descriptor and prints a human-readable
version of it. `hid-decode` takes binary report descriptors, strings of
bytes, and other formats.

```
$ hid-decode /sys/class/input/event5/device/device/report_descriptor
```

# kernel tests

The `hid-tools` repository contains a number of tests exercising the kernel
HID subsystem. The tests are not part of the `pip3` module and must be run
from the git repository. The most convenient invocation of the tests is by
simply calling `pytest`.

```
$ sudo pytest-3
```

See the `pytest` documentation for information on how to run a subset of
tests.

# hidtools python module

Technical limitations require that `hid-tools` ships with a Python module
called `hidtools`. This module is **not** to be used by external
applications.

**The hidtools python module does not provide any API stability guarantee.
It may change at any time**

# License

`hid-tools` is licensed under the GPLv2+.
