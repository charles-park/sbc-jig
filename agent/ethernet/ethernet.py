import asyncio
from .constants import *
import os
from efuse import ODROID_M1

efuse = ODROID_M1()

async def get_speed():
    if os.path.exists(PATH_ETH0):
        with open(PATH_ETH0, 'r') as f:
            speed = f.readline().rstrip()
            return speed
    else:
        return -1

async def read_mac():
    if os.path.exists("/sys/class/net/eth0/address"):
        cmd = 'cat /sys/class/net/eth0/address'
        proc = await asyncio.create_subprocess_shell(cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()
        mac = stdout.decode('utf-8').rstrip()
        return mac

async def write_mac(mac):
    tmp = ' '.join([mac[i:i+2] for i in range(0, len(mac), 2)])
    nodeid = "NODEID = " + tmp + '\n'
    with open(PATH_MAC_CFG, 'r') as file:
        data = file.readlines()
    data[0] = nodeid
    with open(PATH_MAC_CFG, 'w') as file:
        file.writelines(data)

    with open(PATH_MAC_CFG2, 'r') as file:
        data = file.readlines()
    data[0] = nodeid
    with open(PATH_MAC_CFG2, 'w') as file:
        file.writelines(data)

    cmd = './rtu /efuse /# 0 /info'
    proc = await asyncio.create_subprocess_shell(cmd, cwd=PATH_MAC,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    if b'Successful!!!' in stdout:
        return 0
    return 1


async def read_uuid():
    with open('/sys/class/efuse/uuid', 'r', errors='ignore') as f:
        try:
            uuid = f.readline().rstrip().replace('\x00', '')
            return uuid
        except Exception as e:
            uuid = f.readline()
            print(e, uuid)
    return None

async def write_uuid(data):
    result = efuse.provision(data, 0)
    uuid = await read_uuid()
    return uuid

async def ping(ipaddr="8.8.8.8"):
    cmd = f"ping -c 5 {ipaddr} | grep 'packet loss'"
    proc = await asyncio.create_subprocess_shell(cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    if stdout != b'':
        tmp = stdout.decode('utf-8')
        return tmp.split(',')[2].split()[0]

async def set_eth_mode(speed):
    cmd = f"echo odroid | sudo -S ethtool -s eth0 speed {speed} duplex full"
    proc = await asyncio.create_subprocess_shell(cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    if stderr != b'':
        LOG.error(stderr)
    if stderr == b'' and stdout == b'':
        return 0

async def reload_eth0():
    cmd = 'modprobe -r r8152'
    await asyncio.sleep(0.5)
    os.system(cmd)
    cmd = 'modprobe r8152'
    os.system(cmd)
    await asyncio.sleep(0.5)
    cmd = '/etc/init.d/networking restart'
    os.system(cmd)

async def get_ipaddr():
    ipaddr = None
    cmd = 'hostname -I'
    proc = await asyncio.create_subprocess_shell(cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    if stderr != b'':
        LOG.error(stderr)
    return stdout.decode('utf-8').rstrip()

