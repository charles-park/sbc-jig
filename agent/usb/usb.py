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

PATH_NVME = "/sys/devices/platform/3c0800000.pcie/pci*/*:*/*:*:*/nvme/*/nvme*"
PATH_NVME_LINK_SPEED = "/sys/devices/platform/3c0800000.pcie/pci0002:20/0002:20:00.0/current_link_speed"

PATH_SATA = "/sys/devices/platform/fc800000.sata/ata*/host*/target*/*:*/block/sd*"
PATH_SATA_LINK_SPEED = "/sys/class/ata_link/link1/sata_spd"

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
        self.usb3_up = self.create_node('LEFT_UP', USB_LEFT_UP)
        self.usb3_down = self.create_node('LEFT_DOWN', USB_LEFT_DOWN)
        self.usb2_up = self.create_node('RIGHT_UP', USB_RIGHT_UP)
        self.usb2_down = self.create_node('RIGHT_DOWN', USB_RIGHT_DOWN)
        self.sata = self.create_node('SATA', None)
        self.nvme = self.create_node('NVME', None)
        self.usb2_nodes = [self.usb2_up, self.usb2_down]
        self.usb3_nodes = [self.usb3_up, self.usb3_down]

    def create_node(self, label, nodes):
        items = deepcopy(USB_NODE)
        items['label'] = label
        items['nodes'] = nodes
        return items

    def init_node(self, node):
        items = ['state', 'speed', 'r', 'w', 'sdx']
        for k in items:
            node[k] = None

    def print_node(self, node):
        print(f"nodes : {node['nodes']}, speed : {node['speed']}, r : {node['r']}, w : {node['w']}, sdx : {node['sdx']}")

    async def scan_usb2(self, idx):
        for node in self.usb2_nodes[idx]['nodes']:
            path = PATH_DEVICES + node
            if self.node_exists(path) != None:
                speed = await self.read_speed(path)
                return node, speed
        return None, None

    async def scan_sata(self):
        speed = await self.read_sata_link_speed()
        return speed

    async def scan_nvme(self):
        speed = await self.read_nvme_link_speed()
        return speed

    async def scan_usb3(self, idx):
        for node in self.usb3_nodes[idx]['nodes']:
            path = PATH_DEVICES + node
            if self.node_exists(path) != None:
                speed = await self.read_speed(path)
                return node, speed
        return None, None

    async def scan_usb3_up(self):
        for node in self.usb3_up['nodes']:
            speed = await self.read_speed(PATH_DEVICES + node)
            if speed == None:
                LOG.debug(f"usb3 {self.usb3_up['label']} speed None")
                continue
            self.usb3_up['speed'] = speed
            sdx = await self.get_sdx(node)
            self.usb3_up['sdx'] = sdx
            if sdx == None:
                LOG.debug(f"usb3 {self.usb3_up['label']} sdx not found")
                continue
            if self.check_test_file() == None:
                LOG.debug(f"test file does not exists")
                continue
            idx = await self.determine_seek(sdx)
            if idx == None:
                continue
            self.usb3_up['w'] = await self.write_to_disk(sdx, idx)
            self.usb3_up['r'] = await self.read_from_disk(sdx, idx)

    async def scan_usb3_down(self):
        for node in self.usb3_down['nodes']:
            speed = await self.read_speed(PATH_DEVICES + node)
            if speed == None:
                LOG.debug(f"usb3 {self.usb3_down['label']} speed None")
                continue
            self.usb3_down['speed'] = speed
            sdx = await self.get_sdx(node)
            self.usb3_down['sdx'] = sdx
            if sdx == None:
                LOG.debug(f"usb3 {self.usb3_down['label']} sdx not found")
                continue
            if self.check_test_file() == None:
                LOG.debug(f"test file does not exists")
                continue
            idx = await self.determine_seek(sdx)
            if idx == None:
                continue
            self.usb3_down['w'] = await self.write_to_disk(sdx, idx)
            self.usb3_down['r'] = await self.read_from_disk(sdx, idx)
            #print(await self.diff_files(sdx))

    def node_exists(self, path):
        if os.path.exists(path):
            return 1
        return None

    async def read_nvme_link_speed(self):
        if self.node_exists(PATH_NVME_LINK_SPEED) != None:
            with open(PATH_NVME_LINK_SPEED, 'r') as f:
                return f.readline().rstrip()
        return None

    async def read_sata_link_speed(self):
        if self.node_exists(PATH_SATA_LINK_SPEED) != None:
            with open(PATH_SATA_LINK_SPEED, 'r') as f:
                return f.readline().rstrip()
        return None

    async def read_speed(self, path):
        if self.node_exists(path) != None:
            with open(path + '/speed', 'r') as f:
                return f.readline().rstrip()
        return None

    async def get_sdx(self, node):
        path = f"{PATH_DEVICES}{node}{PATH_USB_SDX}"
        sd = "".join(glob(path))[-3:]
        if sd != '':
            return sd
        return None

    async def get_nvme(self):
        path = f"{PATH_NVME}"
        sd = "".join(glob(path)).split('/')[-1]
        if sd != '':
            #check partition
            path += '/nvme*'
            _sd = "".join(glob(path)).split('/')[-1]
            if _sd != '':
                return _sd
            return sd
        return None

    async def get_sata(self):
        path = f"{PATH_SATA}"
        sd = "".join(glob(path))[-3:]
        if sd != '':
            #check partition
            path += '/sd*'
            _sd = "".join(glob(path)).split('/')[-1]
            if _sd != '':
                return _sd
            return sd
        return None

    async def determine_seek(self, sdx):
        size = await self.get_size(sdx)
        if size == None:
            return None
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
            return None
        if stdout != b'':
            return int(stdout.decode('utf-8').rstrip())

    async def read_usb2_speed(self):
        for usb in self.usb2_nodes:
            for _node in usb['nodes']:
                if node == _node:
                    usb['speed'] = await self.read_speed(PATH_DEVICES + node)

    async def read_node_speed(self, node):
        for usb in self.usb_nodes:
            for _node in usb['nodes']:
                if node == _node:
                    usb['speed'] = await self.read_speed(PATH_DEVICES + node)

    async def test_usb(self):
        for device in iter(monitor.poll, None):
            #print(device.device_type, device.action, device.device_path)
            if device.device_type == 'usb_device' and device.action == 'bind':
                node = device.device_path.split('/')[-1]
                #await self.read_node_speed(node)
            elif device.device_type == 'disk':
                tmp = device.device_path
                node = re.split('usb[0-9]/', tmp)[1].split('/')[0]

    def check_test_file(self):
        if os.path.exists('/home/odroid/ramdisk/old_file'):
            return 1
        return None

    async def create_file(self):
        cmd = f"taskset -c 2 head -c 80M </dev/urandom > old_file"
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
        cmd = f"taskset -c 2 dd if=old_file of=/dev/{sdx} seek={seek} bs=8M oflag=direct"
        path = '/home/odroid/ramdisk'
        proc = await asyncio.create_subprocess_shell(cmd, cwd=path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()

        if stderr != b'':
            if b'error' in stderr:
                LOG.error(f"\nstdout : {stdout}\nstderr : {stderr}")
                return None

            tmp = stderr.decode('utf-8').split()
            for idx, s in enumerate(tmp):
                if 'copied' in s:
                    size, unit = tmp[idx-2], tmp[idx-1][:-1]
                    if size != '80' or unit != 'MiB':
                        return None
                    #bandwidth = tmp[idx+3] + tmp[idx+4]
                    bandwidth = tmp[idx+3]
                    return bandwidth

        LOG.error(f"\nstdout : {stdout}\nstderr : {stderr}")
        return None

    async def read_from_disk(self, sdx, skip):
        cmd = f"taskset -c 2 dd if=/dev/{sdx} of=new_{sdx} skip={skip} bs=8M count=10 iflag=direct"
        path = '/home/odroid/ramdisk'
        proc = await asyncio.create_subprocess_shell(cmd, cwd=path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()

        if stderr != b'':
            if b'error' in stderr:
                LOG.error(f"\nstdout : {stdout}\nstderr : {stderr}")
                return None

            tmp = stderr.decode('utf-8').split()
            for idx, s in enumerate(tmp):
                if 'copied' in s:
                    size, unit = tmp[idx-2], tmp[idx-1][:-1]
                    if size != '80' or unit != 'MiB':
                        return None
                    #bandwidth = tmp[idx+3] + tmp[idx+4]
                    bandwidth = tmp[idx+3]
                    return bandwidth
        LOG.error(f"\nstdout : {stdout}\nstderr : {stderr}")
        return None

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
    #print(await usb.create_file())
    #await usb.scan_usb3()
    #mode = await usb.test_usb()
    print(await usb.scan_sata())

if __name__ == "__main__":
    asyncio.run(main())
