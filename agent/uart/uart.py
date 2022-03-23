import asyncio
from serial_asyncio import open_serial_connection
from serial.serialutil import SerialException
import struct
from .constants import *

class Uart():
    def __init__(self, node='/dev/ttyS0', baudrate=115200, model='test'):
        self.model = model
        self.uart = {'node':node, 'alive': -1,
                'r': None, 'w': None, 'baudrate': baudrate}

    async def init_serial(self):
        if self.uart['node'] == None:
            return None
        try:
            self.uart['r'], self.uart['w'] = await open_serial_connection(
                    url=self.uart['node'], baudrate=self.uart['baudrate'])
        except SerialException as e:
            LOG.error(self.uart['r'], self,uart['w'])

        if (type(self.uart['r']) == asyncio.streams.StreamReader) and \
                (type(self.uart['w']) == asyncio.streams.StreamWriter):
                    self.uart['alive'] = 1
                    await self.send('init uart')
                    LOG.warn('Serial initialized')

    async def recv(self):
        while True:
            if self.uart['alive'] != 1:
                await asyncio.sleep(1)
                continue
            try:
                temp = await self.uart['r'].readuntil(b'\n')
                LOG_RECEIVE.debug(f'msg : {temp}')
                header = struct.unpack('!4s2s', temp[:6])
                size = int(header[1].decode('utf-8').rstrip('\x00'))
                msg = struct.unpack(f'!{size}s', temp[6:6+size])
                yield await self.check_msg_header(msg[0])
            except SerialException as e:
                LOG.error(f"serial {self.uart['node']} connection closed")
                self.uart['alive'] = 0
            except struct.error as e:
                LOG.error(e)
            await asyncio.sleep(0.1)

    async def check_msg_header(self, msg):
        temp = msg.decode('utf-8').rstrip().split(',')
        LOG_RECEIVE.debug(temp)
        cmd = temp[0]
        data = temp[1:]
        return cmd, data

    async def available_uart(self):
        while True:
            if self.uart['alive'] != 1:
                await self.init_serial()
            await asyncio.sleep(1)

    async def write(self, data):
        if self.uart['alive'] == 1:
            self.uart['w'].write(str.encode(data))

    async def read(self):
        if self.uart['alive'] == 1:
            #temp = await self.uart['r'].readuntil(b'\n')
            temp = await self.uart['r'].readline()
            print(temp)

    async def send(self, msg):
        if self.uart['alive'] != 1:
            await asyncio.sleep(2)
        if self.uart['alive'] == 1:
            length_msg = str(len(msg))
            bytearr = struct.pack('!4s2s', str.encode(self.model),
                    str.encode(length_msg))
            bytearr += struct.pack(f'!{length_msg}s', str.encode(msg))
            LOG_SEND.debug(f'[{msg}]')
            self.uart['w'].write(bytearr + b'\n')

async def main():
    uart = Uart()
    task = await asyncio.ensure_future(uart.init_serial())
    await uart.send('hello123')
    await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
