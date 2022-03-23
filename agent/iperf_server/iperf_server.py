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


TCP_ECHO_SERVER_IP = '0.0.0.0'
TCP_ECHO_SERVER_PORT = 8888

class IperfServer():
    def __init__(self, loop, channel):
        self.loop = loop
        self.which_iperf3 = None
        self.iperf3_proc = None
        self.channel = channel

    def is_iperf3_exist(self):
        self.which_iperf3 = which('iperf3')
        if self.which_iperf3 is None:
            return False
        else:
            return True


    async def handle_tcp_echo(self, reader, writer):
        data = await reader.read(100)

        message = data.decode()
        addr = writer.get_extra_info('peername')
        print(f'Received "{message}" from {addr}')

        if 'iperf' in message:
            if 'start' in message:
                asyncio.ensure_future(self.stop_iperf())
                asyncio.ensure_future(self.start_iperf())
            elif 'stop' in message:
                asyncio.ensure_future(self.stop_iperf())
            else:
                print('Unknown command.')
        writer.close()

    async def run_performance(self):
        try:
            cmd = 'service cpufrequtils restart'
            proc = await asyncio.create_subprocess_shell(cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await proc.communicate()

            stdout = stdout.decode('utf-8')
            print(stdout, stderr)
            if 'error' in stdout:
                print(stdout)

        except Exception as err:
            print(f'\t{err}')


    async def start_iperf(self):
        try:
            if self.iperf3_proc is None:
                self.iperf3_proc = await asyncio.create_subprocess_exec(
                    self.which_iperf3, '-s',
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
            if self.iperf3_proc is not None:
                self.iperf3_proc.terminate()
                self.iperf3_proc = None
        except Exception as err:
                print(f'Error on line {sys.exc_info()[-1].tb_lineno}', end='\n')
                print(f'\t{err}')

    async def run(self):
        if self.is_iperf3_exist():
            server_coro = asyncio.start_server(
                    self.handle_tcp_echo, TCP_ECHO_SERVER_IP, TCP_ECHO_SERVER_PORT, loop=self.loop)
            #server = self.loop.run_until_complete(server_coro)
            await asyncio.sleep(1)
            server = await server_coro

            print('Serving on {}'.format(server.sockets[0].getsockname()))
            '''
            try:
                loop.run_forever()
            except KeyboardInterrupt:
                print('Keyboard interrupt occured!')
                print('Program will be closed.')
                pass
            
            server.close()
            loop.run_until_complete(server.wait_closed())
            loop.close()
            '''

        else:
            print('iperf3 doesn not exist. Please install that using "apt install iperf3"')
