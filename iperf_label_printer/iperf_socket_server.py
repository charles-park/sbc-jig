#!/usr/bin/env python3
#
# iperf3 supervisor of the external server
#
# You need the following pip packages
# - asyncio
#

from shutil import which
import sys
import subprocess
import asyncio
import psutil
from label_printer import MacPrinter

psutil.cpu_count()
p = psutil.Process()
p.cpu_affinity([1])

TCP_ECHO_SERVER_IP = '0.0.0.0'
TCP_ECHO_SERVER_PORT = 8888

FORUM = 'forum.odroid.com'

class IperfServer():
    def __init__(self):
        self.iperf3_proc = None
        if self.is_iperf3_exist() == False:
            print('iperf3 doesn not exist. Please install that using "apt install iperf3"')
        self.mac_printer = MacPrinter()

    def is_iperf3_exist(self):
        if which('iperf3') == None:
            return False
        else:
            return True

    async def handle_tcp_echo(self, reader, writer):
        data = await reader.read(200)

        message = data.decode()
        addr = writer.get_extra_info('peername')
        print(f'Received "{message}" from {addr}')

        if 'iperf' in message:
            if 'start' in message:
                await self.stop_iperf()
                await self.start_iperf()
            elif 'stop' in message:
                await self.stop_iperf()
            else:
                print('Unknown command.')
        if 'mac' in message:
            mac = message.split(',')[1]
            if mac.startswith('001e06'):
                if len(mac) == 12 and not ':' in mac:
                    temp = [mac[i:i+2] for i in range(0, len(mac), 2)]
                    mac = ':'.join(temp)
                    self.mac_printer.label_print(0, FORUM, mac)
        if 'error' in message:
            errors = message[6:]
            self.mac_printer.label_print(0, errors, None, 1)
            '''
            errors = message.split(',')[1:]
            lines = []
            tmp = ""
            for error in errors:
                if len(tmp + error) < 20:
                    tmp += error + ','
                else:
                    lines.append(tmp)
                    tmp = error
            '''
        ''' Charles add : 2022-04-14 for next jig '''
        if 'left-m' in message:
            mac = message.split(',')[1]
            if mac.startswith('001e06'):
                if len(mac) == 12 and not ':' in mac:
                    temp = [mac[i:i+2] for i in range(0, len(mac), 2)]
                    mac = ':'.join(temp)
                    self.mac_printer.label_print(0, FORUM, mac)
        if 'left-e' in message:
            errors = message[7:]
            self.mac_printer.label_print(0, errors, None, 1)
        if 'right-m' in message:
            mac = message.split(',')[1]
            if mac.startswith('001e06'):
                if len(mac) == 12 and not ':' in mac:
                    temp = [mac[i:i+2] for i in range(0, len(mac), 2)]
                    mac = ':'.join(temp)
                    self.mac_printer.label_print(1, FORUM, mac)
        if 'right-e' in message:
            errors = message[8:]
            self.mac_printer.label_print(1, errors, None, 1)

            #self.mac_printer.label_print(0, lines[0], lines[1])
        if 'version' in message:
            sbuff = bytes("20220419", encoding='utf-8')
            writer.write(sbuff)
        writer.close()

    async def start_iperf(self):
        try:
            if self.iperf3_proc == None:
                cmd = "iperf3 -s"
                self.iperf3_proc = await asyncio.create_subprocess_exec('iperf3', '-s',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE)            
                stdout, stderr = await self.iperf3_proc.communicate()

                stdout = stdout.decode('utf-8')
                if 'error' in stdout:
                    print(stdout)

        except Exception as err:
                print(f'Error on line {sys.exc_info()[-1].tb_lineno}', end='\n')
                print(f'\t{err}')

    async def stop_iperf(self):
        try:
            if self.iperf3_proc != None:
                self.iperf3_proc.terminate()
                self.iperf3_proc = None
        except Exception as err:
                print(f'Error on line {sys.exc_info()[-1].tb_lineno}', end='\n')
                print(f'\t{err}')

async def main():
    iperf_server = IperfServer()
    server = await asyncio.start_server(
        iperf_server.handle_tcp_echo, TCP_ECHO_SERVER_IP, TCP_ECHO_SERVER_PORT)
    addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
    print(f'Serving on {addrs}')

    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    asyncio.run(main())

