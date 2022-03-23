from gpio import GPIO
import asyncio
from asyncio import ensure_future as aef
from odroid_factory_api import API_MANAGER
from functools import wraps
from utils.log import init_logger
from copy import deepcopy

from task import Component
from task import Task
from task import cancelled_exception
from label_printer import MacPrinter

LOG = init_logger('', testing_mode='info')

USB_R_U = '1.2'
USB_R_D = '1.3'

FORUM = 'forum.odroid.com'

UART_IPERF_EXTERNAL_HOST_MAP = {
        USB_R_U: '192.168.0.200',
        USB_R_D: '192.168.0.200',
}

class HC4():
    mac_printer = MacPrinter()
    uart = '/dev/ttyS0'
    def __init__(self):
        self.model = 'HC4'
        self.pins = GPIO(self.model)
        self.gpio = self.pins.gpio
        self.pwrs = self.pins.pwrs
        self.leds_sys = self.pins.leds_sys
        self.leds_eth = self.pins.leds_eth
        self.led_hdd = self.pins.led_hdd
        self.hdmi = self.pins.hdmi
        self.items = None
        self.vddee = 0
        self.cnt_vddee = 1
        self.api_manager = API_MANAGER(board='hc4')

        self.labels_item = ['onoff', 'ipaddr', 'eth_speed', 'led_sys', 'led_eth',
                'gpio', 'iperf', 'uuid', 'write_uuid', 'led_hdd',
                'hdmi', 'uart', 'usb2', 'lspci', 'sata_r0', 'sata_r1',
                'sata_w0', 'sata_w1', 'mnt0', 'mnt1', 'finish']
        self.items = {k:Component() for k in self.labels_item}

        self.labels_gpio = [x.label for x in self.gpio]
        self.items_gpio = {k:Component() for k in self.labels_gpio}

        self.task_check_ipaddr = Task(self.check_ipaddr, 10)
        self.task_check_uuid = Task(self.check_uuid)
        self.task_usb2 = Task(self.check_usb2, 20)
        self.task_eth_speed = Task(self.check_eth_speed)
        self.task_sata = Task(self.check_sata, 10)
        self.task_sata0 = Task(self.check_sata0)
        self.task_sata1 = Task(self.check_sata1)
        self.task_gpio = Task(self.check_gpio)
        self.task_hdmi = Task(self.check_hdmi)
        self.task_iperf = Task(self.check_iperf, 30)
        self.task_led_sys = Task(self.check_led_sys)
        self.task_led_eth = Task(self.check_led_eth)
        self.task_led_hdd = Task(self.check_led_hdd)

    def init_item(self, item):
        for k, v in self.items.items():
            if k == item:
                v.req = v.ack = v.ret = v.seq = v.value = v.okay = v.tmp = None
                v.flag_text = 1
                label = ['led_eth', 'led_sys', 'led_hdd', 'lspci']
                for i in label:
                    if i == k:
                        v.flag_text = 0
                if k == 'iperf':
                    v.flag_text = 2
                elif k == 'hdmi' or k == 'gpio':
                    v.flag_text = 3
                v.update = 1

    def init_variables(self):
        self.cnt_vddee = 1
        self.vddee = 0
        for k, v in self.items.items():
            if k == 'name' or k == 'uart' or k == 'onoff':
                continue
            v.req = v.ack = v.ret = v.seq = v.value = v.okay = v.tmp = None
            if k == 'finish':
                v.okay = 2
            label = ['led_eth', 'led_sys', 'led_hdd', 'finish', 'lspci']
            for i in label:
                if i == k:
                    v.flag_text = 0
            if k == 'iperf':
                v.flag_text = 2
            if k == 'hdmi' or k == 'gpio':
                v.flag_text = 3
            v.update = 1

    async def check_finish(self):
        if self.items['finish'].okay == 2:
            _finish = deepcopy(self.items)
            del(_finish['finish'])
            finish = any(v.okay == None for k, v in _finish.items())
            if finish != False:
                return

            aef(self.uart.send('cmd,finish'))
            err = []
            for k, v in _finish.items():
                if v.okay != 1:
                    err.append(k)
            if len(err) > 0:
                self.fail_items('finish')
                tmp = ",".join(err)
                line0 = tmp[:18]
                line1 = tmp[19:]
                self.mac_printer.label_print(self.channel, line0, line1)
                results = await self.api_manager.update_record({
                    'all_pass': False })
                return
            self.okay_items('finish')
            mac = self.items['uuid'].value
            if mac.startswith('001e06'):
                if len(mac) == 12 and not ':' in mac:
                    temp = [mac[i:i+2] for i in range(0, len(mac), 2)]
                    mac = ':'.join(temp)
                    self.mac_printer.label_print(self.channel, FORUM, mac)
                    results = await self.api_manager.update_record({
                        'all_pass': True })
                    return
            self.fail_items('finish')
            self.mac_printer.label_print(self.channel, "MAC Fail", "MAC Fail")
            results = await self.api_manager.update_record({
                'all_pass': False })

    async def monitor_pwr(self):
        uart = None
        onoff = None
        async for _onoff, vddee in self.adc.check_pwr(self.pwrs):
            if vddee != None:
                self.vddee += float(vddee)
                self.cnt_vddee += 1
            if uart != self.uart.uart['alive']:
                self.items['uart'].value = self.uart.uart['node']
                uart = self.items['uart'].okay = self.uart.uart['alive']
                self.items['uart'].update = 1

            if onoff != _onoff:
                onoff = self.items['onoff'].okay = _onoff
                if _onoff:
                    await self.init_sequence()
                    self.okay_items('onoff', 'ON')
                else:
                    self.fail_items('onoff', 'OFF')
            await self.check_finish()

    async def sequence_main(self):
        while True:
            if self.seq_main == 1:
                self.seq_main = 2

                await self.task_check_ipaddr.run()
                await self.task_check_uuid.run()
                aef(self.task_eth_speed.run())
                aef(self.task_usb2.run())
                aef(self.task_iperf.run())
                aef(self.task_sata.run())
                aef(self.task_hdmi.run())
                aef(self.task_gpio.run())
                aef(self.task_led_sys.run())

            elif self.seq_main == 2:
                flag = self.items['iperf'].okay
                if flag == 1 or flag == 0:
                    aef(self.task_led_eth.run())
                    self.seq_main = 3

            elif self.seq_main == 3:
                flag = self.items['sata_w0'].okay
                if flag == 0 or flag == 1:
                    aef(self.task_led_hdd.run())
                    self.seq_main = 4
            await asyncio.sleep(1)

    @cancelled_exception()
    async def check_ipaddr(self, timeout):
        cnt = 0
        while cnt < timeout:
            self.items['ipaddr'].ack = None
            aef(self.uart.send('cmd,eth,ipaddr'))
            await self.wait_ack(self.items['ipaddr'], 5)
            ret = await self.wait_ret(self.items['ipaddr'], 5)
            if ret != 0:
                await asyncio.sleep(1)
                continue
            if self.items['ipaddr'].value.startswith('192.168.'):
                self.okay_items('ipaddr')
                return
            cnt += 1
            await asyncio.sleep(1)
        self.fail_items('ipaddr')

    @cancelled_exception()
    async def check_eth_speed(self):
        self.items['eth_speed'].ack = None
        aef(self.uart.send('cmd,eth,speed'))
        ack = await self.wait_ack(self.items['eth_speed'], 5)
        if ack != 0:
            return
        ret = await self.wait_ret(self.items['eth_speed'])
        if ret != 0:
            return
        if self.items['eth_speed'].value == '1000':
            self.okay_items('eth_speed')
        else:
            self.fail_items('eth_speed')
        speed = int(self.items['eth_speed'].value)
        results = await self.api_manager.update_record({
            'ethernet_bandwidth': speed,
            'ethernet_ping': 0})
        results = await self.api_manager.update_record({
            'ethernet_bandwidth': 0,
            'ethernet_ping': 0})

    @cancelled_exception()
    async def check_usb2(self, timeout):
        count = 0
        while count < timeout:
            self.items['usb2'].ack = None
            aef(self.uart.send('cmd,usb2,speed'))
            ack = await self.wait_ack(self.items['usb2'], 5)
            await self.wait_ret(self.items['usb2'])
            if self.items['usb2'].value == '480':
                self.okay_items('usb2')
                speed = int(self.items['usb2'].value)
                results = await self.api_manager.update_record({
                            'usb_2_bandwidth': speed})
                return
            count += 1
            await asyncio.sleep(1)

        self.fail_items('usb2')
        speed = int(self.items['usb2'].value)
        results = await self.api_manager.update_record({
                    'usb_2_bandwidth': speed})
        results = await self.api_manager.update_record({
                    'usb_2_bandwidth': 0})

    @cancelled_exception()
    async def check_uuid(self):
        self.items['uuid'].ack = None
        aef(self.uart.send('cmd,eth,uuid'))
        ack = await self.wait_ack(self.items['uuid'], 5)
        if ack != 0:
            return
        ret = await self.wait_ret(self.items['uuid'], 5)
        if ret != 0:
            self.items['write_uuid'].okay = 0
            return
        mac = self.items['uuid'].tmp[-12:]
        if mac.startswith('001e06'):
            self.api_manager.mac_addr = mac
            self.api_manager.uuid_mac = self.items['uuid'].tmp
            await self.api_manager.update_record({
                'uuid': self.items['uuid'].tmp})
            self.okay_items('uuid', mac)
            self.items['write_uuid'].okay = 1
        else:
            await self.write_uuid()

    @cancelled_exception()
    async def write_uuid(self):
        mac_string = await self.api_manager.request_mac_addr()
        if mac_string == None:
            self.items['write_uuid'].okay = 0
            self.fail_items('uuid', 'API fail')
            return None

        self.items['write_uuid'].ack = None
        aef(self.uart.send('cmd,eth,write_uuid,' + mac_string))
        ack = await self.wait_ack(self.items['write_uuid'], 5)
        if ack != 0:
            self.fail_items('uuid', 'No ACK')
            return
        ret = await self.wait_ret(self.items['write_uuid'], 5)
        if ret != 0:
            self.fail_items('uuid', 'No RET')
            self.items['write_uuid'].okay = 0
            return

        mac = self.items['write_uuid'].value[-12:]
        if mac.startswith('001e06'):
            self.okay_items('uuid', mac)
            self.items['write_uuid'].okay = 1
            await self.api_manager.update_record({
                'uuid': self.items['uuid'].tmp})
        else:
            self.items['write_uuid'].okay = 0
            self.fail_items('uuid')


    @cancelled_exception()
    async def check_hdmi(self):
        for i in range(4):
            self.items['hdmi'].ack = None
            aef(self.uart.send(f'cmd,hdmi,{i}'))
            await self.wait_ack(self.items['hdmi'], 5)
            await self.wait_ret(self.items['hdmi'], 10)
            ret = await self.adc.check_hdmi(self.hdmi, seq=i)
            if len(ret) != 0:
                self.items['hdmi'].tmp = ""
                for i in ret:
                    self.items['hdmi'].tmp += i[0]
                self.fail_items('hdmi')
                return
            if i == 3:
                if len(ret) == 0:
                    self.okay_items('hdmi')

    @cancelled_exception()
    async def check_gpio(self):
        self.items['gpio'].tmp = ""
        self.items['gpio'].ack = None
        aef(self.uart.send('cmd,gpio'))
        await self.wait_ack(self.items['gpio'], 5)

        gpios = deepcopy(self.gpio)
        for i in self.items_gpio:
            self.items['gpio'].ack = None
            aef(self.uart.send(f'cmd,gpio,{i}'))
            await self.wait_ack(self.items['gpio'], 5)
            await self.wait_ret(self.items['gpio'], 5)
            result = await self.adc.read_times(gpios, i)
            if type(result) == list:
                self.items_gpio[i].okay = 0
                LOG.error(f'{result}')
                self.items['gpio'].tmp += result[0]
                for i in result:
                    for idx, j in enumerate(gpios):
                        if i == j.label:
                            del(gpios[idx])
            elif result == 0:
                self.items_gpio[i].okay = 1
        if all(v.okay for k, v in self.items_gpio.items()):
            self.okay_items('gpio')
        else:
            self.fail_items('gpio')

    @cancelled_exception()
    async def check_led_hdd(self):
        ret = await self.adc.check_hdd_led(self.led_hdd, seq=0)
        if len(ret) != 0:
            self.fail_items('led_hdd')
            return

        self.items['led_hdd'].ack = None
        aef(self.uart.send('cmd,led_hdd,1'))
        ack = await self.wait_ack(self.items['led_hdd'], 5)
        if ack != 0:
            LOG.error(f"wait_ack LED_HDD")
            return
        ret = await self.wait_ret(self.items['led_hdd'], 10)
        if ret != 0:
            LOG.error("wait_ret : LED_HDD")
            return

        ret = await self.adc.check_hdd_led(self.led_hdd, seq=1)
        if len(ret) == 0:
            self.okay_items('led_hdd')
        else:
            self.fail_items('led_hdd')

    @cancelled_exception()
    async def check_led_sys(self):
        self.items['led_sys'].ack = None
        aef(self.uart.send('cmd,led_sys,0'))
        ack = await self.wait_ack(self.items['led_sys'], 5)
        if ack != 0:
            LOG.error(f"wait_ack LED_SYS")
            return
        ret = await self.wait_ret(self.items['led_sys'], 10)
        if ret != 0:
            LOG.error("wait_ret : LED_SYS")
            return

        ret = await self.adc.check_sys_led(self.leds_sys, seq=0)
        if len(ret) != 0:
            self.fail_items('led_hdd')
            return

        self.items['led_sys'].ack = None
        aef(self.uart.send('cmd,led_sys,1'))
        ack = await self.wait_ack(self.items['led_sys'], 5)
        if ack != 0:
            LOG.error(f"wait_ack LED_SYS")
            return
        ret = await self.wait_ret(self.items['led_sys'], 10)
        if ret != 0:
            LOG.error("wait_ret : LED_SYS")
            return

        ret = await self.adc.check_sys_led(self.leds_sys, seq=1)
        if len(ret) == 0:
            self.okay_items('led_sys')
        else:
            self.fail_items('led_sys')

    @cancelled_exception()
    async def check_led_eth(self):
        self.items['led_eth'].ack = None
        aef(self.uart.send('cmd,led_eth,1000'))
        ack = await self.wait_ack(self.items['led_eth'], 5)
        if ack != 0:
            LOG.error(f"wait_ack LED_ETH")
            return
        ret = await self.wait_ret(self.items['led_eth'], 10)
        if ret != 0:
            LOG.error("wait_ret : LED_ETH")
            return

        ret = await self.adc.check_eth_led(self.leds_eth, speed=1000)
        if len(ret) != 0:
            self.fail_items('led_eth')
            return

        self.items['led_eth'].ack = None
        aef(self.uart.send('cmd,led_eth,100'))
        ack = await self.wait_ack(self.items['led_eth'], 5)
        if ack != 0:
            LOG.error(f"wait_ack LED_ETH")
            return
        ret = await self.wait_ret(self.items['led_eth'], 10)
        if ret != 0:
            LOG.error("wait_ret : LED_ETH")
            return

        ret = await self.adc.check_eth_led(self.leds_eth, speed=100)
        if len(ret) == 0:
            self.okay_items('led_eth')
        else:
            self.fail_items('led_eth')

    @cancelled_exception()
    async def _check_sata(self, ch):
        self.items[f'mnt{ch}'].ack = None
        aef(self.uart.send(f'cmd,sata,get,{ch}'))
        ack = await self.wait_ack(self.items[f'mnt{ch}'], 5)
        if ack != 0:
            self.fail_items([f'mnt{ch}', f'sata_r{ch}', f'sata_w{ch}'])
            return
        ret = await self.wait_ret(self.items[f'mnt{ch}'], 10)
        if ret != 0:
            self.fail_items([f'mnt{ch}', f'sata_r{ch}', f'sata_w{ch}'])
            return
        if type(self.items[f'mnt{ch}'].value) == str:
            if self.items[f'mnt{ch}'].value.startswith('sd'):
                self.okay_items(f'mnt{ch}')
            else:
                self.fail_items([f'mnt{ch}', f'sata_r{ch}', f'sata_w{ch}'])
                return
        else:
            self.fail_items([f'mnt{ch}', f'sata_r{ch}', f'sata_w{ch}'])
            return

        cnt = 0
        okay = None
        while cnt < 30 and okay != 0 and okay != 1:
            okay = self.items['iperf'].okay
            cnt += 1
            await asyncio.sleep(1)

        self.items[f'sata_r{ch}'].ack = None
        aef(self.uart.send(f'cmd,sata,read,{ch}'))
        ack = await self.wait_ack(self.items[f'sata_r{ch}'], 10)
        if ack != 0:
            self.fail_items([f'sata_r{ch}', f'sata_w{ch}'])
            return
        ret = await self.wait_ret(self.items[f'sata_r{ch}'], 20)
        if ret != 0:
            self.fail_items([f'sata_r{ch}', f'sata_w{ch}'])
            return
        if self.items[f'sata_r{ch}'].value == '512MiB':
            unit = self.items[f'sata_r{ch}'].tmp[-4:]
            speed = int(self.items[f'sata_r{ch}'].tmp[:-4])
            if unit != 'MB/s':
                self.items[f'sata_r{ch}'].okay = 0
                self.fail_items(f'sata_r{ch}', self.items[f'sata_r{ch}'].tmp)
            else:
                if speed > 200:
                    self.okay_items(f'sata_r{ch}', self.items[f'sata_r{ch}'].tmp)
                else:
                    self.fail_items(f'sata_r{ch}', self.items[f'sata_r{ch}'].tmp)
        
        self.items[f'sata_w{ch}'].ack = None
        aef(self.uart.send(f'cmd,sata,write,{ch}'))
        ack = await self.wait_ack(self.items[f'sata_w{ch}'], 10)
        if ack != 0:
            self.fail_items([f'sata_w{ch}'])
            return
        ret = await self.wait_ret(self.items[f'sata_w{ch}'], 20)
        if ret != 0:
            self.fail_items([f'sata_w{ch}'])
            return
        if self.items[f'sata_w{ch}'].value == '512MiB':
            unit = self.items[f'sata_w{ch}'].tmp[-4:]
            speed = int(self.items[f'sata_w{ch}'].tmp[:-4])
            if unit != 'MB/s':
                self.fail_items(f'sata_w{ch}', self.items[f'sata_w{ch}'].tmp)
            else:
                if speed > 200:
                    self.okay_items(f'sata_w{ch}', self.items[f'sata_w{ch}'].tmp)
                else:
                    self.fail_items(f'sata_w{ch}', self.items[f'sata_w{ch}'].tmp)
        else:
            self.fail_items([f'sata_w{ch}'])

    @cancelled_exception()
    async def check_sata1(self):
        await self._check_sata(1)

    @cancelled_exception()
    async def check_sata0(self):
        await self._check_sata(0)

    @cancelled_exception()
    async def check_sata(self, timeout):
        self.items['lspci'].ack = None
        aef(self.uart.send(f'cmd,sata,lspci'))
        ack = await self.wait_ack(self.items['lspci'], 5)
        if ack != 0:
            return
        ret = await self.wait_ret(self.items['lspci'], timeout)
        if ret != 0:
            results = await self.api_manager.update_record({
                'lspci_sata_recognition': -1000 })
            self.fail_items('lspci')
            for ch in range(2):
                self.fail_items([f'mnt{ch}', f'sata_r{ch}', f'sata_w{ch}'])
            return
        if self.items['lspci'].value != '0':
            results = await self.api_manager.update_record({
                'lspci_sata_recognition': -1001 })
            self.fail_items('lspci')
            for ch in range(2):
                self.fail_items([f'mnt{ch}', f'sata_r{ch}', f'sata_w{ch}'])
            return
        results = await self.api_manager.update_record({
            'lspci_sata_recognition': 1 })
        self.okay_items('lspci')

        aef(self.task_sata0.run())
        aef(self.task_sata1.run())

    @cancelled_exception()
    async def check_iperf(self, timeout):
        self.items['iperf'].seq = 0
        place = UART_IPERF_EXTERNAL_HOST_MAP[self.uart.uart['place']]

        self.items['iperf'].ack = None
        aef(self.uart.send(f'cmd,eth,iperf,{place}'))
        ack = await self.wait_ack(self.items['iperf'], 5)
        if ack != 0:
            return
        else:
            self.items['iperf'].okay = 2
            self.items['iperf'].value = "Running..."
            self.items['iperf'].tmp = ""
            self.items['iperf'].update = 1

        ret = await self.wait_ret(self.items['iperf'], timeout)
        if ret != 0:
            return
        if self.items['iperf'].value == "None":
            self.fail_items('iperf', "Fail")
            return

        _bandwidth = self.items['iperf'].value.split()
        _loss = self.items['iperf'].tmp[:-1]
        bandwidth = float(_bandwidth[0])
        loss = float(_loss)
        if _bandwidth[1][-4] == 'K':
            self.fail_items('iperf')
            results = await self.api_manager.update_record({
                'iperf_rx_udp_bandwidth': bandwidth/1000,
                'iperf_rx_udp_loss_rate': loss })
            return
        if _bandwidth[1][-4] == 'G':
            self.fail_items('iperf')
            results = await self.api_manager.update_record({
                'iperf_rx_udp_bandwidth': bandwidth*1000,
                'iperf_rx_udp_loss_rate': loss })
            return
        results = await self.api_manager.update_record({
            'iperf_rx_udp_bandwidth': bandwidth,
            'iperf_rx_udp_loss_rate': loss })
        if bandwidth > 800 and loss < 10:
            self.okay_items('iperf')
        else:
            self.fail_items('iperf')

