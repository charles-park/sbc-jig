from utils.log import init_logger
from copy import deepcopy
from glob import glob
from random import randint
from .constants import *
import asyncio
import pyudev
import os
import re

context = pyudev.Context()
monitor = pyudev.Monitor.from_netlink(context)
monitor.filter_by('usb')
monitor.filter_by('block')

LOG = init_logger('', testing_mode='info')

PATH_DEVICES = "/sys/bus/usb/devices/"
PATH_USB_SDX = "/*:*/host*/target*/*:*/block/sd*"

USB_NODE = {k:None for k in ['label', 'nodes', 'state', 'speed', 'r', 'w', 'sdx']}

# USB3
# 7-1, 8-1
#USB_LEFT_UP = ['fd000000']
USB_LEFT_UP = ['7-1', '8-1']
# 5-1, 6-1
#USB_LEFT_DOWN = ['fcc00000']
USB_LEFT_DOWN = ['5-1', '6-1']

# USB2
# 1-1, 3-1
#USB_RIGHT_UP = ['fd800000', 'fd840000']
USB_RIGHT_UP = ['1-1', '3-1']
# 2-1, 4-1
#USB_RIGHT_DOWN = ['fd8c0000', 'fd880000']
USB_RIGHT_DOWN = ['2-1', '4-1']


class USB():
    def __init__(self):
        self.l_u = self.create_node('LEFT_UP', USB_LEFT_UP)
        self.l_d = self.create_node('LEFT_DOWN', USB_LEFT_DOWN)
        self.r_u = self.create_node('RIGHT_UP', USB_RIGHT_UP)
        self.r_d = self.create_node('RIGHT_DOWN', USB_RIGHT_DOWN)
        self.usb2_nodes = [self.r_u, self.r_d]
        self.usb3_nodes = [self.l_u, self.l_d]

    def create_node(self, label, nodes):
        items = deepcopy(USB_NODE)
        items['label'] = label
        items['nodes'] = nodes
        return items

    async def scan_usb2(self):
        for usb in self.usb2_nodes:
            for node in usb['nodes']:
                usb['speed'] = await self.read_speed(PATH_DEVICES + node)
                print(usb['speed'])

    async def scan_usb(self):
        for usb in self.usb_nodes:
            for node in usb['nodes']:
                usb['speed'] = await self.read_speed(PATH_DEVICES + node)
                sdx = await self.get_sdx(node)
                usb['sdx'] = sdx
                if sdx == -1:
                    continue
                idx = await self.determine_seek(sdx)
                print(f'write to {sdx}')
                usb['w'] = await self.write_to_disk(sdx, idx)
                print(f'read from {sdx}')
                usb['r'] = await self.read_from_disk(sdx, idx)
                print(usb['w'], usb['r'], usb['speed'])
                print(await self.diff_files(sdx))

    async def read_speed(self, path):
        if os.path.exists(path):
            with open(path + '/speed', 'r') as f:
                return f.readline().rstrip()
        return -1

    async def get_sdx(self, node):
        path = f"{PATH_DEVICES}{node}{PATH_USB_SDX}"
        sd = "".join(glob(path))[-3:]
        if sd == '':
            return -1
        return sd

    async def determine_seek(self, sdx):
        size = await self.get_size(sdx)
        size_MiB = int(size/1024)
        '''
        We use 'randint' instread of:
        tmp = random.random()*1000%(int(size_MiB/80))
        '''
        val_seek  = randint(1, int(size_MiB/80) -2)
        return val_seek

    async def get_size(self, sdx):
        cmd = f"fdisk -s /dev/{sdx}"
        proc = await asyncio.create_subprocess_shell(cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()
        if stderr != b'':
            LOG.error(f"\nstdout : {stdout}\nstderr : {stderr}")
        if stdout != b'':
            return int(stdout.decode('utf-8').rstrip())

    async def read_usb2_speed(self):
        for usb in self.usb2_nodes:
            for _node in usb['nodes']:
                if node == _node:
                    usb['speed'] = await self.read_speed(PATH_DEVICES + node)
                    print(usb['speed'], usb['label'])

    async def read_node_speed(self, node):
        for usb in self.usb_nodes:
            for _node in usb['nodes']:
                if node == _node:
                    usb['speed'] = await self.read_speed(PATH_DEVICES + node)
                    print(usb['speed'], usb['label'])

    async def test_usb(self):
        for device in iter(monitor.poll, None):
            #print(device.device_type, device.action, device.device_path)
            if device.device_type == 'usb_device' and device.action == 'bind':
                node = device.device_path.split('/')[-1]
                #await self.read_node_speed(node)
            elif device.device_type == 'disk':
                tmp = device.device_path
                node = re.split('usb[0-9]/', tmp)[1].split('/')[0]
                print(node)
                #print(device.action)
                #print(device.device_path)

    async def create_file(self):
        cmd = f"head -c 80M </dev/urandom > old_file"
        path = '/home/odroid/ramdisk'
        proc = await asyncio.create_subprocess_shell(cmd, cwd=path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()
        if stderr != b'':
            LOG.error(f"\nstdout : {stdout}\nstderr : {stderr}")
            return 1
        return 0

    async def write_to_disk(self, sdx, seek):
        cmd = f"dd if=old_file of=/dev/{sdx} seek={seek} bs=8M oflag=direct"
        path = '/home/odroid/ramdisk'
        proc = await asyncio.create_subprocess_shell(cmd, cwd=path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()

        if stderr != b'':
            if b'error' in stderr:
                LOG.error(f"\nstdout : {stdout}\nstderr : {stderr}")
                return 1

            tmp = stderr.decode('utf-8').split()
            for idx, s in enumerate(tmp):
                if 'copied' in s:
                    size, unit = tmp[idx-2], tmp[idx-1][:-1]
                    if size != '80' or unit != 'MiB':
                        return 2
                    bandwidth = tmp[idx+3] + tmp[idx+4]
                    return bandwidth

        LOG.error(f"\nstdout : {stdout}\nstderr : {stderr}")
        return 3

    async def read_from_disk(self, sdx, skip):
        cmd = f"dd if=/dev/{sdx} of=new_{sdx} skip={skip} bs=8M count=10 iflag=direct"
        path = '/home/odroid/ramdisk'
        proc = await asyncio.create_subprocess_shell(cmd, cwd=path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()

        if stderr != b'':
            if b'error' in stderr:
                LOG.error(f"\nstdout : {stdout}\nstderr : {stderr}")
                return 1

            tmp = stderr.decode('utf-8').split()
            for idx, s in enumerate(tmp):
                if 'copied' in s:
                    size, unit = tmp[idx-2], tmp[idx-1][:-1]
                    if size != '80' or unit != 'MiB':
                        return 2
                    bandwidth = tmp[idx+3] + tmp[idx+4]
                    return bandwidth
        LOG.error(f"\nstdout : {stdout}\nstderr : {stderr}")
        return 3

    async def diff_files(self, sdx):
        cmd = f'diff old_file new_{sdx}'
        path = '/home/odroid/ramdisk'
        proc = await asyncio.create_subprocess_shell(cmd, cwd=path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()
        if stderr != b'' or stdout != b'':
            LOG.error(f"\nstdout : {stdout}\nstderr : {stderr}")
            return 1
        return 0

async def main():
    usb = USB()
    print(await usb.create_file())
    await usb.scan_usb()
    mode = await usb.test_usb()
    print(mode)

if __name__ == "__main__":
    asyncio.run(main())
