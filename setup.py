#!/usr/bin/python3

from setuptools import setup

setup(name='hid-tools',
      version='0.1',
      description='HID tools',
      long_description=open('README.md', 'r').read(),
      url='http://gitlab.freedesktop.org/libevdev/hid-tools',
      packages=['hidtools'],
      author='Benjamin Tissoires',
      author_email='benjamin.tissoires@redhat.com',
      license='GPL',
      entry_points={
          "console_scripts": [
              'hid-recorder = hidtools.record:main',
              'hid-replay = hidtools.replay:main',
              'hid-parse= hidtools.parse_hid:main',
              'hid-parse-rdesc = hidtools.parse_rdesc:main',
              ]
      },
      classifiers=[
          'Development Status :: 3 - Alpha',
          'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.6'
      ],
      data_files=[('/usr/share/man/man1', ['man/hid-recorder.1',
                                           'man/hid-replay.1'])],
      python_requires='>=3.6',
      include_package_data=True,
      )
