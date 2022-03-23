#!/usr/bin/python3

import os
import fcntl
import struct
import uuid

def checksum(s):
    sum = 0

    for i in range(len(s)):
        sum += ord(s[i])

    return sum % 256

class ODROID_M1:
    magic = 'HKM1'
    ioctl_magic = 0x7673

    req = None
    session = None

    def __init__(self):
        self.req = None
        self.session = None

    def provision(self, data, offset = 0):
        if data == None:
            print("E: failed to get board identity...")
            return False

        data = str(data).replace("-", "")
        if len(data) > 64:
            print("E: data is too long, must be <64")
            return False

        buf = struct.pack("4sIIB32s",
                self.magic.encode('utf-8'),
                offset,
                len(data),
                checksum(data),
                data.encode('utf-8'))

        try:
            fd = os.open('/dev/efuse', os.O_RDWR)
            ret = fcntl.ioctl(fd, self.ioctl_magic, buf)
            print("ret = {0}".format(ret))
            os.close(fd)
        except OSError as err:
            print("E: {0}".format(err))
            return False

        print('I: success - {}'.format(data))

        return True

    def dump(self):
        try:
            fd = os.open('/dev/efuse', os.O_RDWR)
            ret = fcntl.ioctl(fd, 0x7674, "1234")
            print("ret = {0}".format(ret))
            os.close(fd)
        except OSError as err:
            print("E: {0}".format(err))
            return False

        return True

    def clear(self, offset):
        buf = struct.pack("4sIIB32s",
                self.magic.encode('utf-8'),
                offset,
                0,
                0,
                ''.encode('utf-8'))
        try:
            fd = os.open('/dev/efuse', os.O_RDWR)
            ret = fcntl.ioctl(fd, 0x7675, buf)
            print("ret = {0}".format(ret))
            os.close(fd)
        except OSError as err:
            print("E: {0}".format(err))
            return False

        print('I: success - {}'.format(data))

        return True


if __name__ == "__main__":
    board = ODROID_M1()

    cnt = 0
    with open('mac', 'r') as f:
        cnt = int(f.readline())
    with open('mac', 'w') as f:
        f.write(str(cnt+1))
    print(cnt)

    data = uuid.uuid1(128954990592+cnt)

    print(data)
    #success = board.provision(data, 96)
    #success = board.clear(96)
    if not success:
        print('ERROR')
    else:
        print('OK')
