import asyncio
from asyncio import ensure_future as aef
from odroid_factory_api import API_MANAGER
from functools import wraps
from utils.log import init_logger
from copy import deepcopy
from usb import USB
import ethernet
import aiohttp
import iperf
import os
from evtest import Evtest

from task import Component
from task import Task
from task import cancelled_exception
import configparser
#import criteria

LOG = init_logger('', testing_mode='info')

class M1():
    def __init__(self):
        self.model = 'M1'
        self.api_manager = API_MANAGER(board='m1')
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        self.cfg_sata = self.config['sata']
        self.cfg_nvme = self.config['nvme']
        self.cfg_usb2 = self.config['usb2']
        self.cfg_usb3 = self.config['usb3']
        self.cfg_iperf = self.config['iperf']
        self.usb = USB()
        self.ev = Evtest()

        self.items = None
        self.flag0 = ['finish', 'usb2_up', 'usb2_down', 'spi_btn', 'usb3_up_speed',
                'usb3_up_sdx', 'usb3_up_rw', 'usb3_down_speed', 'usb3_down_sdx',
                'usb3_down_rw', 'sata_speed', 'sata_sdx', 'sata_rw', 'nvme_speed',
                'nvme_sdx', 'nvme_rw', 'eth_speed', 'mac', 'iperf', 'ipaddr_printer', 'hp_det', 'ir']
        self.flag1 = ['ping', 'ping_printer', 'usb3_up_diff', 'usb3_down_diff',
                'sata_diff', 'nvme_diff']
        self.items0 = {k:Component(flag_text=1) for k in self.flag0}
        self.items1  = {k:Component(flag_text=0) for k in self.flag1}
        self.items = {**self.items0, **self.items1}

        self.task_spi_btn = Task(self.check_spi_btn)
        self.task_usb2 = Task(self.check_usb2)
        self.task_usb3 = Task(self.check_usb3)
        self.task_sata = Task(self.check_sata)
        self.task_nvme = Task(self.check_nvme)
        self.task_eth_speed = Task(self.check_eth_speed)
        self.task_iperf = Task(self.check_iperf)
        self.task_mac = Task(self.check_mac)
        self.task_ping = Task(self.check_ping)
        self.task_printer = Task(self.check_printer)
        self.task_hp_detect = Task(self.check_hp_detect)
        self.task_ir = Task(self.check_ir)
        self.task_play_music = Task(self.play_music)
        self.task_scan_iperf_server = Task(self.scan_iperf_server)

    def init_item(self, item):
        for k, v in self.items.items():
            if k == item:
                if k == 'finish':
                    v.okay = 2
                    continue
                v.text = v.ack = v.ret = v.value = v.okay = None
                v.update = 1

    def init_variables(self):
        for k, v in self.items.items():
            if k == 'finish':
                v.okay = 2
                continue
            v.text = v.ack = v.ret = v.value = v.okay = None
            v.update = 1

    async def cancel_tasks(self):
        aef(self.task_usb2.cancelled())
        aef(self.task_usb3.cancelled())
        aef(self.task_sata.cancelled())
        aef(self.task_nvme.cancelled())
        aef(self.task_eth_speed.cancelled())
        aef(self.task_printer.cancelled())
        aef(self.task_mac.cancelled())
        aef(self.task_ping.cancelled())
        aef(self.task_hp_detect.cancelled())
        aef(self.task_ir.cancelled())
        aef(self.task_iperf.cancelled())
        aef(self.task_play_music.cancelled())

    async def finish(self):
        ipaddr = self.cfg_iperf.get('ipaddr')
        if self.items['mac'].value != None:
            await iperf.control_external_iperf_server(ipaddr, 'mac,' + self.items['mac'].value)
        _finish = deepcopy(self.items)
        del(_finish['finish'])
        err = set()
        for k, v in _finish.items():
            if v.okay != 1:
                if 'usb3' in k:
                    err.add(k[:k.find('_', 5)])
                elif 'nvme' in k or 'sata' in k:
                    err.add(k[:k.find('_', 4)])
                else:
                    err.add(k)
        if len(err) > 0:
            self.fail_item('finish', 'FINISH')
            ipaddr = self.cfg_iperf.get('ipaddr')
            await iperf.control_external_iperf_server(ipaddr, "error," + ",".join(err))
            return
        self.okay_item('finish', 'FINISH')

    async def sequence_main(self):
        tasks = []
        while True:
            if self.seq_main == 1:
                #aef(ethernet.set_eth_mode('1000'))
                await self.usb.create_file()
                self.seq_main = 2
                aef(self.task_spi_btn.run())
                tasks.append(aef(self.task_printer.run()))
                tasks.append(aef(self.task_iperf.run()))
                tasks.append(aef(self.task_mac.run()))
                tasks.append(aef(self.task_ping.run()))
                tasks.append(aef(self.task_eth_speed.run()))
                tasks.append(aef(self.task_hp_detect.run()))
                tasks.append(aef(self.task_ir.run()))
                tasks.append(aef(self.task_sata.run()))
                tasks.append(aef(self.task_nvme.run()))
                tasks.append(aef(self.task_usb3.run()))
                tasks.append(aef(self.task_usb2.run()))
                tasks.append(aef(self.task_play_music.run()))

            elif self.seq_main == 2:
                _finish = deepcopy(self.items)
                del(_finish['finish'])
                finish = all(v.okay == 1 for k, v in _finish.items())
                if finish == True:
                    await self.finish()
                    self.seq_main = 3
                    LOG.error("FINISH!!!!!!!!!!!!")
                '''
                if all([task.done() for task in tasks]):
                        await self.finish()
                        self.seq_main = 3
                '''

            await asyncio.sleep(1)

    @cancelled_exception()
    async def check_printer(self):
        ipaddr = self.cfg_iperf.get('ipaddr')
        self.okay_item('ipaddr_printer', ipaddr)

    @cancelled_exception()
    async def set_printer_ip(self, ipaddr):
        self.init_item('ping_printer')
        self.config.set('iperf', 'ipaddr', ipaddr)
        with open('config.ini', 'w') as cfg:
            self.config.write(cfg)
        await self.check_printer()

    @cancelled_exception()
    async def play_music(self):
        while True:
            cmd = "amixer set 'Playback Path' 'HP'"
            proc = await asyncio.create_subprocess_shell(cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await proc.communicate()
            cmd = "aplay piano.wav"
            proc = await asyncio.create_subprocess_shell(cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await proc.communicate()
            await asyncio.sleep(1)

    async def poweroff(self):
        cmd = f"./run_poweroff.sh"
        proc = await asyncio.create_subprocess_shell(cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()
        if stderr != b'':
            LOG.error(stderr)
        if stderr == b'' and stdout == b'':
            return 0

    @cancelled_exception()
    async def check_ir(self):
        cnt_press = 0
        cnt_release = 0
        cnt_eth = {'green':0, 'yellow':0}
        if self.ev.device_ir == None:
            LOG.error("No ir event available")
            self.fail_item('ir')
        async for label, value in self.ev.read_ir():
            if label == 'enter':
                if value == 1:
                    cnt_press += 1
                elif value == 0:
                    cnt_release += 1
            elif label == 'eth_green' and value == 0:
                cnt_eth['green'] += 1
                aef(ethernet.set_eth_mode('100'))
            elif label == 'eth_yellow' and value == 0:
                cnt_eth['yellow'] += 1
                aef(ethernet.set_eth_mode('1000'))
            elif label == 'poweroff' and value == 0:
                aef(self.poweroff())
            elif label == 'scan' and value == 0:
                aef(self.task_scan_iperf_server.run())
            elif label == 'print' and value == 0:
                await self.finish()
            elif label == 'mac_rewrite' and value == 0:
                print ("==> 2022.04.13 mac rewrite added for charles")
                await aef(self.task_mac.run())
            if cnt_press > 0 and cnt_release > 0 and cnt_eth['green'] > 0:
                self.okay_item('ir', f"press : {cnt_press}, out : {cnt_release}, eth_green : {cnt_eth['green']}, eth_yellow : {cnt_eth['yellow']}")
            else:
                self.ready_item('ir', f"press : {cnt_press}, out : {cnt_release}, eth_green : {cnt_eth['green']}, eth_yellow : {cnt_eth['yellow']}")

    @cancelled_exception()
    async def check_hp_detect(self):
        cnt_in = 0
        cnt_out = 0
        if self.ev.device_hp == None:
            LOG.error("No hp_det event available")
            self.fail_item('hp_det')
        async for value in self.ev.read_hp_det():
            if value == 0:
                cnt_out += 1
            elif value == 1:
                cnt_in += 1
            if cnt_in > 0 and cnt_out > 0:
                self.okay_item('hp_det', f"in : {cnt_in}, out : {cnt_out}")
            else:
                self.ready_item('hp_det', f"in : {cnt_in}, out : {cnt_out}")

    @cancelled_exception()
    async def check_ping(self):
        while True:
            loss = await ethernet.ping()
            if loss == '0%':
                if self.items['ping'].okay != 1:
                    self.okay_item('ping')
            else:
                self.fail_item('ping')

            ipaddr = self.cfg_iperf.get('ipaddr')
            if await iperf.control_external_iperf_server(ipaddr, 'bind'):
                if self.items['ping_printer'].okay != 1:
                    self.okay_item('ping_printer')
            else:
                self.fail_item('ping_printer')
            await asyncio.sleep(1)

    @cancelled_exception()
    async def check_mac(self):
        uuid = await ethernet.read_uuid()
        mac = uuid[-12:]
        if mac.startswith('001e06'):
            self.items['mac'].value = mac
            self.api_manager.mac_addr = mac
            self.api_manager.uuid_mac = uuid
            await self.api_manager.update_record({
                'uuid': uuid})
            self.okay_item('mac', mac)
            return

        uuid = await self.api_manager.request_mac_addr()
        await ethernet.write_uuid(uuid)

        uuid = await ethernet.read_uuid()
        mac = uuid[-12:]
        if mac.startswith('001e06'):
            self.items['mac'].value = mac
            self.api_manager.mac_addr = mac
            self.api_manager.uuid_mac = uuid
            await self.api_manager.update_record({
                'uuid': uuid})
            self.okay_item('mac', mac)
            return
        self.fail_item('mac')

    @cancelled_exception()
    async def check_spi_btn(self):
        count_err = 0
        count_click = 0
        while True:
            cmd = "hexdump -C /dev/mtdblock0 -n 1000 | head -10 | grep EFI"
            proc = await asyncio.create_subprocess_shell(cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await proc.communicate()
            if not b'EFI PART' in stdout:
                count_err += 1
            if count_err > 0:
                self.okay_item('spi_btn', 'SPI_BTN')
                return

            await asyncio.sleep(0.3)

    @cancelled_exception()
    async def _check_usb2(self, idx, place):
        node, speed = await self.usb.scan_usb2(idx)
        if node == None:
            self.ready_item(f'usb2_{place}', speed)
            return
        if speed != self.cfg_usb2.get('speed', '480'):
            self.ready_item(f'usb2_{place}', speed)
            return
        self.okay_item(f'usb2_{place}', speed)

    @cancelled_exception()
    async def check_usb2(self):
        items_usb2 = ['usb2_up', 'usb2_down']
        while True:
            await asyncio.sleep(2)
            if self.items['usb2_up'].okay != 1:
                await self._check_usb2(0, 'up')
            if self.items['usb2_down'].okay != 1:
                await self._check_usb2(1, 'down')
    
    @cancelled_exception()
    async def _check_usb3(self, idx, place):
        self.init_usb3_items(place)
        self.usb.init_node(self.usb.usb3_nodes[idx])
        node, speed = await self.usb.scan_usb3(idx)
        if node == None:
            self.ready_item(f'usb3_{place}_speed', speed)
            return
        if speed != self.cfg_usb3.get('speed', '5000'):
            self.fail_item(f'usb3_{place}_speed', speed)
            return
        self.okay_item(f'usb3_{place}_speed', speed)
        sdx = await self.usb.get_sdx(node)
        if sdx == None:
            return
        elif not sdx.startswith('sd'):
            self.fail_item(f'usb3_{place}_sdx', sdx)
            return
        self.okay_item(f'usb3_{place}_sdx', sdx)
        if self.usb.check_test_file() == None:
            LOG.debug(f"test file does not exists")
            return
        offset = await self.usb.determine_seek(sdx)
        if offset == None:
            return
        self.ready_item(f'usb3_{place}_rw')
        await asyncio.sleep(1)
        w = await self.usb.write_to_disk(sdx, offset)
        r = await self.usb.read_from_disk(sdx, offset)
        if r == None or w == None:
            self.fail_item(f'usb3_{place}_rw', str(r) + ',' + str(w))
            return
        else:
            norm_r = self.cfg_usb3.getfloat('r', 30)
            norm_w = self.cfg_usb3.getfloat('w', 20)
            if float(r) > norm_r and float(w) > norm_w:
                self.okay_item(f'usb3_{place}_rw', str(r) + ',' + str(w))
            else:
                self.fail_item(f'usb3_{place}_rw', str(r) + ',' + str(w))
            if await self.usb.diff_files(sdx) == 0:
                self.okay_item(f'usb3_{place}_diff')
            else:
                self.fail_item(f'usb3_{place}_diff')


    @cancelled_exception()
    async def check_usb3(self):
        items_usb3_up = ['usb3_up_speed', 'usb3_up_sdx', 'usb3_up_rw', 'usb3_up_diff']
        items_usb3_down = ['usb3_down_speed', 'usb3_down_sdx', 'usb3_down_rw', 'usb3_down_diff']
        await asyncio.sleep(2)
        while True:
            await asyncio.sleep(1)
            if any([self.items[usb].okay != 1 for usb in items_usb3_up]):
                await self._check_usb3(0, 'up')
            if any([self.items[usb].okay != 1 for usb in items_usb3_down]):
                await self._check_usb3(1, 'down')
        
    @cancelled_exception()
    async def check_nvme(self):
        items_nvme = ['nvme_speed', 'nvme_sdx', 'nvme_rw', 'nvme_diff']
        count = 0
        while True:
            await asyncio.sleep(2)
            if any([self.items[nvme].okay != 1 for nvme in items_nvme]):
                self.init_disk_items('nvme')
                self.usb.init_node(self.usb.nvme)
                speed = await self.usb.scan_nvme()
                if speed == None or speed == '<unknown>':
                    self.ready_item('nvme_speed', speed)
                    continue
                _speed = speed.split()
                norm_speeds = self.cfg_nvme['speed'].split()
                if _speed[1] != norm_speeds[1]:
                    self.fail_item('nvme_speed', speed)
                    continue
                if float(_speed[0]) < float(norm_speeds[0]):
                    self.fail_item('nvme_speed', speed)
                    continue
                self.okay_item('nvme_speed', speed)
                sdx = await self.usb.get_nvme()
                if sdx == None:
                    continue
                elif not sdx.startswith('nvme'):
                    self.fail_item(f'nvme_sdx', sdx)
                    continue
                self.okay_item(f'nvme_sdx', sdx)
                if self.usb.check_test_file() == None:
                    LOG.debug(f"test file does not exists")
                    continue
                offset = await self.usb.determine_seek(sdx)
                if offset == None:
                    continue
                await asyncio.sleep(2)
                w = await self.usb.write_to_disk(sdx, offset)
                r = await self.usb.read_from_disk(sdx, offset)
                if r != None and w != None:
                    count += 1
                    self.ready_item('nvme_rw', str(r) + ',' + str(w))
                    norm_r = self.cfg_nvme.getfloat('r', 60)
                    norm_w = self.cfg_nvme.getfloat('w', 30)
                    if float(r) > norm_r and float(w) > norm_w:
                        self.okay_item('nvme_rw')
                    else:
                        self.fail_item('nvme_rw', str(r) + ',' + str(w))
                    if await self.usb.diff_files(sdx) == 0:
                        self.okay_item(f'nvme_diff')
                    else:
                        self.fail_item(f'nvme_diff')
                if count >= self.cfg_nvme.getint('retry', 3):
                    return

    @cancelled_exception()
    async def check_sata(self):
        items_sata = ['sata_speed', 'sata_sdx', 'sata_rw', 'sata_diff']
        count = 0
        await asyncio.sleep(2)
        while True:
            await asyncio.sleep(2)
            if any([self.items[sata].okay != 1 for sata in items_sata]):
                self.init_sata_items()
                self.usb.init_node(self.usb.sata)
                speed = await self.usb.scan_sata()
                if speed == None or speed == '<unknown>':
                    self.ready_item('sata_speed', speed)
                    continue
                _speed = speed.split()
                norm_speeds = self.cfg_sata['speed'].split()
                if _speed[1] != norm_speeds[1]:
                    self.fail_item('sata_speed', speed)
                    continue
                if float(_speed[0]) < float(norm_speeds[0]):
                    self.fail_item('sata_speed', speed)
                    continue
                self.okay_item('sata_speed', speed)
                sdx = await self.usb.get_sata()
                if sdx == None:
                    continue
                elif not sdx.startswith('sd'):
                    self.fail_item(f'sata_sdx', sdx)
                    continue
                self.okay_item(f'sata_sdx', sdx)
                if self.usb.check_test_file() == None:
                    LOG.debug(f"test file does not exists")
                    continue
                offset = await self.usb.determine_seek(sdx)
                if offset == None:
                    continue
                await asyncio.sleep(2)
                w = await self.usb.write_to_disk(sdx, offset)
                r = await self.usb.read_from_disk(sdx, offset)
                if r != None and w != None:
                    count += 1
                    self.ready_item('sata_rw', str(r) + ',' + str(w))
                    norm_r = self.cfg_sata.getfloat('r', 60)
                    norm_w = self.cfg_sata.getfloat('w', 30)
                    if float(r) > norm_r and float(w) > norm_w:
                        self.okay_item('sata_rw')
                    else:
                        self.fail_item('sata_rw', str(r) + ',' + str(w))
                    if await self.usb.diff_files(sdx) == 0:
                        self.okay_item(f'sata_diff')
                    else:
                        self.fail_item(f'sata_diff')
                if count >= self.cfg_sata.getint('retry', 3):
                    return

    def init_usb3_items(self, place):
        items = [f'usb3_{place}_speed', f'usb3_{place}_rw', f'usb3_{place}_sdx', f'usb3_{place}_diff']
        for item in items:
            self.items[item].text = None
            self.items[item].okay = None
            self.items[item].update = 1

    def init_usb3_down_items(self):
        items = ['usb3_down_speed', 'usb3_down_rw', 'usb3_down_sdx']
        for item in items:
            self.items[item].okay = None
            self.items[item].update = 1

    def init_sata_items(self):
        items = ['sata_speed', 'sata_sdx', 'sata_rw', 'sata_diff']
        for item in items:
            self.items[item].okay = None
            self.items[item].update = 1

    def init_disk_items(self, item):
        items = [f'{item}_speed', f'{item}_sdx', f'{item}_rw', f'{item}_diff']
        for item in items:
            self.items[item].okay = None
            self.items[item].update = 1

    @cancelled_exception()
    async def usb3_speed(self, usb):
        self.items[f'{usb}_speed'].ack = None
        if ack != 0:
            return
        if ret != 0:
            return

        speed = self.items[f'{usb}_speed'].value
        self.items[f'{usb}_speed'].text = speed
        if speed == '5000':
            self.okay_item(f'{usb}_speed')
        else:
            self.fail_item(f'{usb}_speed')

    @cancelled_exception()
    async def usb3_sdx(self, usb):
        self.items[f'{usb}_sdx'].ack = None
        if ack != 0:
            return
        if ret != 0:
            return

        sdx = self.items[f'{usb}_sdx'].value
        self.items[f'{usb}_sdx'].text = sdx
        if sdx.startswith('sd'):
            self.okay_item(f'{usb}_sdx')
        else:
            self.fail_item(f'{usb}_sdx')

    @cancelled_exception()
    async def usb3_rw(self, usb):
        self.items[f'{usb}_rw'].ack = None
        sdx = self.items[f'{usb}_sdx'].value
        if not sdx.startswith('sd'):
            self.fail_item(f'{usb}_rw')
            return
        if ack != 0:
            return
        if ret != 0:
            return

        val = self.items[f'{usb}_rw'].value
        if len(val) == 3 and type(val) == list:
            self.items[f'{usb}_rw'].text = f'{val[0]},{val[1]},{val[2]}'
            if len(val[0]) == 1 or len(val[1]) == 1:
                self.fail_item(f'{usb}_rw')
                return
            read = float(val[0][:-4])
            write = float(val[1][:-4])
            if read > 80 and write > 30:
                if val[2] != '0':
                    self.fail_item(f'{usb}_rw')
                else:
                    self.okay_item(f'{usb}_rw')
            else:
                self.fail_item(f'{usb}_rw')
        else:
            self.fail_item(f'{usb}_rw')

    @cancelled_exception()
    async def check_eth_speed(self):
        while True:
            speed = await ethernet.get_speed()
            if speed == '1000':
                self.okay_item('eth_speed', speed)
                return
            else:
                self.fail_item('eth_speed', speed)
            await asyncio.sleep(2)

    @cancelled_exception()
    async def check_iperf(self):
        await asyncio.sleep(5)
        while True:
            try:
                await asyncio.sleep(1)
                self.ready_item('iperf', 'Waiting...')
                ipaddr = self.cfg_iperf.get('ipaddr')
                ret_iperf = await asyncio.wait_for(iperf.iperf_udp(ipaddr, 1), timeout=30)
                if ret_iperf == False or ret_iperf == None:
                    continue
                #881 Mb/s,0%
                tmp = ret_iperf.split(',')
                bandwidth = float(tmp[0].split()[0])
                loss = float(tmp[1][:-1])
                if tmp[0][-4:] != 'Mb/s':
                    self.fail_item('iperf', ret_iperf)
                    continue
                norm_bw = self.cfg_iperf.getfloat('bandwidth', 700)
                norm_loss = self.cfg_iperf.getfloat('loss', 10)
                if bandwidth > norm_bw and loss < norm_loss:
                    self.okay_item('iperf', ret_iperf)
                    return
                self.fail_item('iperf', ret_iperf)
            except Exception as e:
                print(e)

    @cancelled_exception()
    async def scan_iperf_server(self):
        cmd = 'hostname -I'
        proc = await asyncio.create_subprocess_shell(cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()
        if stderr != b'':
            LOG.error(stderr)
        _ipaddr = stdout.decode('utf-8').rstrip()
        ipaddr = _ipaddr.split('.')
        grep = "| grep 192.168 | awk '{print$5}'"
        cmd = f"nmap -sP {ipaddr[0]}.{ipaddr[1]}.{ipaddr[2]}.* {grep}"
        proc = await asyncio.create_subprocess_shell(cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()
        if stderr == b'':
            tmp = stdout.decode('utf-8').split()
            res = [aef(iperf.control_external_iperf_server(ip, 'bind')) for ip in tmp]
            while True:
                for idx, task in enumerate(res):
                    if task.done():
                        if await task:
                            await self.set_printer_ip(tmp[idx])
                            return
                await asyncio.sleep(1)
