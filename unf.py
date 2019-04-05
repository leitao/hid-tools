#!/usr/bin/python3

import sys

def quirk(line):
    if 'Buf' in line:
        print(line, end='')
        return True
    if 'NoPref' in line:
        print(line, end='')
        return True
    return False

if len(sys.argv) < 2:
    print("Usage\n")
    print(sys.argv[0] + ": <python file>")
    exit(255)

file = sys.argv[1]
fp = open(file, 'r')
line = fp.readline()
while line:
    if "f'" in line:
        if quirk(line):
            line = fp.readline()
            continue

        x = line.split("f'")
        print(x[0], end='')
        print("'", end='')
        y = x[1].split("'")
        inner = y[0]
        app = inner + "'.format(**locals())"

        print(app, end='')
#        try:
        print(y[1], end='')
#        except IndexError:
#            print("ERROR")
#            print(line)
#            sys.exit(-255)

        try:
            print(x[2], end='')
        except IndexError:
            pass
    else:
        print(line, end='')
    line = fp.readline()
