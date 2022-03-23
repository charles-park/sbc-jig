from gpio import GPIO
import asyncio
from asyncio import ensure_future as aef
from odroid_factory_api import API_MANAGER
from functools import wraps
from utils.log import init_logger
from copy import deepcopy
import aiohttp
import os

from task import Component
from task import Task
from task import cancelled_exception

LOG = init_logger('', testing_mode='info')

class XU4():
    def __init__(self):
        self.model = 'XU4'
        self.api_manager = API_MANAGER(board='xu4')
        self.pins = GPIO(self.model)
        self.gpios = self.pins.gpios
        self.pwrs = self.pins.pwrs
        self.fan = self.pins.fan
        self.led_sys = self.pins.led_sys
        self.led_pwr = self.pins.led_pwr
        self.led_eth = self.pins.led_eth
        self.hdmi = self.pins.hdmi

        self.items = None
        self.flag0 = ['led_sys', 'led_eth', 'led_pwr', 'ping', 'fan']
        self.flag1 = ['uart', 'usb2', 'onoff', 'gpio', 'usb_fw', 'hdmi',
                'mac_addr', 'ipaddr', 'usb3_up_speed', 'usb3_down_speed',
                'usb3_up_rw', 'usb3_down_rw', 'finish', 'adc0', 'adc3',
                'boot_mode', 'pwr_key', 'usb3_up_sdx', 'usb3_down_sdx',
                'eth_speed']
        self.items0 = {k:Component(flag_text=0) for k in self.flag0}
        self.items1  = {k:Component(flag_text=1) for k in self.flag1}
        self.items = {**self.items0, **self.items1}

        self.labels_gpio = [x.label for x in self.gpios]
        self.items_gpio = {k:Component(k) for k in self.labels_gpio}

        self.task_led_sys = Task(self.check_led_sys)
        self.task_led_eth = Task(self.check_led_eth)

        self.task_usb2 = Task(self.check_usb2, 30)
        self.task_usb3 = Task(self.check_usb3, 50)
        self.task_gpio = Task(self.check_gpio)
        self.task_eth_speed = Task(self.check_eth_speed, 30)
        self.task_gpio_hdmi = Task(self.check_gpio_hdmi)
        self.task_usb_fw = Task(self.check_usb_fw)
        self.task_mac_addr = Task(self.check_mac_addr)
        self.task_ipaddr = Task(self.check_ipaddr, 20)
        self.task_ping = Task(self.check_ping)
        self.task_adc = Task(self.check_adc)
        self.task_fan = Task(self.check_fan)
        self.task_pwr_key = Task(self.check_pwr_key, 30)
        self.task_check_switch = Task(self.check_switch, 30)

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
            if k == 'uart' or k == 'onoff':
                continue
            v.text = v.ack = v.ret = v.value = v.okay = None
            v.update = 1

    async def cancel_tasks(self):
        aef(self.task_led_sys.cancelled())
        aef(self.task_led_eth.cancelled())
        aef(self.task_usb2.cancelled())
        aef(self.task_usb3.cancelled())
        aef(self.task_gpio.cancelled())
        aef(self.task_eth_speed.cancelled())
        aef(self.task_gpio_hdmi.cancelled())
        aef(self.task_usb_fw.cancelled())
        aef(self.task_mac_addr.cancelled())
        aef(self.task_ipaddr.cancelled())
        aef(self.task_ping.cancelled())
        aef(self.task_adc.cancelled())
        aef(self.task_fan.cancelled())
        aef(self.task_pwr_key.cancelled())
        aef(self.task_check_switch.cancelled())



    async def check_finish(self):
        if self.items['finish'].okay == 2:
            _finish = deepcopy(self.items)

            del(_finish['finish'])
            finish1 = any(v.okay == None for k, v in _finish.items())
            finish2 = any(v.okay == 2 for k, v in _finish.items())
            finish = finish1 or finish2
            if finish != False:
                return

            err = []
            for k, v in _finish.items():
                if v.okay != 1:
                    err.append(k)
            print(err)
            if len(err) > 0:
                self.fail_item('finish', 'FINISH')
                return
            self.okay_item('finish', 'FINISH')
            aef(self.uart.send('cmd,finish'))

    async def monitor_pwr(self):
        uart = None
        onoff = None
        async for _onoff in self.adc.check_pwr(self.pwrs):
            if uart != self.uart.uart['alive']:
                self.items['uart'].text = self.uart.uart['node']
                uart = self.items['uart'].okay = self.uart.uart['alive']
                self.items['uart'].update = 1

            if onoff != _onoff:
                onoff = self.items['onoff'].okay = _onoff
                if _onoff:
                    await self.init_sequence()
                    self.okay_item('onoff', 'ON')
                    self.ready_item('finish', 'FINISH', 2)
                else:
                    aef(self.cancel_tasks())
                    self.fail_item('onoff', 'OFF')

            await self.check_finish()

    async def sequence_main(self):
        tasks = []
        while True:
            if self.seq_main == 1:
                self.seq_main = 2
                #SD
                tasks.append(aef(self.task_gpio_hdmi.run()))
                tasks.append(aef(self.task_mac_addr.run()))
                tasks.append(aef(self.task_usb_fw.run()))
                tasks.append(aef(self.task_adc.run()))
                tasks.append(aef(self.task_ipaddr.run()))
                tasks.append(aef(self.task_fan.run()))
                tasks.append(aef(self.task_led_sys.run()))
                tasks.append(aef(self.task_check_switch.run()))
                tasks.append(aef(self.task_pwr_key.run()))
                tasks.append(aef(self.task_usb2.run()))
                tasks.append(aef(self.task_gpio.run()))
                tasks.append(aef(self.task_eth_speed.run()))


            elif self.seq_main == 2:
                if all([task.done() for task in tasks]):
                    if self.items['boot_mode'].okay != 1:
                        self.ready_item('finish', 'FINISH', 0)
                        aef(self.uart.send('cmd,finish'))
                        self.seq_main = 3
                    self.ready_item('finish', 'REBOOT', 2)
                    aef(self.uart.send('cmd,reboot'))
                    self.seq_main = 3

            elif self.seq_main == 4:
                #EMMC
                self.seq_main = 5
                aef(self.task_usb3.run())
                aef(self.task_led_eth.run())

            await asyncio.sleep(1)


    @cancelled_exception()
    async def check_ipaddr(self, timeout):
        count = 0
        while count < timeout:
            self.items['ipaddr'].ack = None
            aef(self.uart.send('cmd,ipaddr'))
            ack = await self.wait_ack('ipaddr')
            if ack != 0:
                return
            ret = await self.wait_ret('ipaddr', 10)
            if ret != 0:
                return
            ipaddr = self.items['ipaddr'].value
            if ipaddr.startswith('192.168.'):
                self.okay_item('ipaddr', ipaddr)
                return
            count += 1
            await asyncio.sleep(1)
        self.fail_item('ipaddr', self.items['ipaddr'].value)

    @cancelled_exception()
    async def check_adc(self):
        self.items['adc0'].ack = None
        aef(self.uart.send('cmd,adc0'))
        ack = await self.wait_ack('adc0')
        if ack != 0:
            self.fail_item('adc3')
            return
        ret = await self.wait_ret('adc0', 10)
        if ret != 0:
            self.fail_item('adc3')
            return
        adc0 = self.items['adc0'].value
        volt_0 = 1.8*int(adc0)/4096
        if volt_0 > 1.1 and volt_0 < 1.5:
            self.okay_item('adc0', adc0)
        else:
            self.fail_item('adc0', adc0)
            self.fail_item('adc3')

        self.items['adc3'].ack = None
        aef(self.uart.send('cmd,adc3'))
        ack = await self.wait_ack('adc3')
        if ack != 0:
            return
        ret = await self.wait_ret('adc3', 10)
        if ret != 0:
            return
        adc3 = self.items['adc3'].value
        volt_3 = 1.8*int(adc3)/4096
        if volt_3 > 0.35 and volt_3 < 5.3:
            self.okay_item('adc3', adc3)
        else:
            self.fail_item('adc3', adc3)

    @cancelled_exception()
    async def check_ping(self):
        self.items['ping'].ack = None
        aef(self.uart.send('cmd,ping'))
        ack = await self.wait_ack('ping')
        if ack != 0:
            return
        ret = await self.wait_ret('ping', 10)
        if ret != 0:
            return
        # packet loss 0%
        loss = self.items['ping'].value
        if loss == '0%':
            self.okay_item('ping')
        else:
            self.fail_item('ping')

    @cancelled_exception()
    async def check_mac_addr(self):
        cnt = 0
        while self.items['ipaddr'].okay != 1:
            if cnt > 10:
                break
            cnt += 1
            await asyncio.sleep(1)
        await self.task_ping.run()
        self.items['mac_addr'].ack = None
        aef(self.uart.send('cmd,mac_addr'))
        ack = await self.wait_ack('mac_addr')
        if ack != 0:
            return
        ret = await self.wait_ret('mac_addr', 10)
        if ret != 0:
            return
        mac_addr = self.items['mac_addr'].value
        if mac_addr.startswith('00:1e:06:3'):
            self.okay_item('mac_addr', mac_addr)
            return

        self.items['mac_addr'].ack = None
        mac_addr = await self.api_manager.request_mac_addr()
        aef(self.uart.send(f'cmd,mac_addr,{mac_addr}'))
        ack = await self.wait_ack('mac_addr')
        if ack != 0:
            return
        ret = await self.wait_ret('mac_addr', 15)
        if ret != 0:
            return

        mac_addr = self.items['mac_addr'].value
        self.okay_item('mac_addr', mac_addr)
        if mac_addr.startswith('00:1e:06:3'):
            self.okay_item('mac_addr')
        else:
            self.fail_item('mac_addr')


    @cancelled_exception()
    async def check_pwr_key(self, timeout):
        self.items['pwr_key'].ack = None
        self.ready_item('pwr_key', 'PWR_KEY', None)
        aef(self.uart.send(f'cmd,pwr_key,0,{timeout}'))
        ack = await self.wait_ack('pwr_key')
        if ack != 0:
            return
        ret = await self.wait_ret('pwr_key')
        if ret != 0:
            return
        if self.items['pwr_key'].value != '0':
            self.fail_item('pwr_key')
            return

        self.items['pwr_key'].ack = None
        aef(self.uart.send(f'cmd,pwr_key,1,{timeout}'))
        ack = await self.wait_ack('pwr_key')
        if ack != 0:
            return
        ret = await self.wait_ret('pwr_key', timeout, 'PUSH')
        if ret != 0:
            return
        if self.items['pwr_key'].value == '0':
            print('okay')
            self.okay_item('pwr_key', 'PWR_KEY')
            return
        self.fail_item('pwr_key')

    @cancelled_exception()
    async def check_usb2(self, timeout):
        while timeout:
            self.items['usb2'].ack = None
            aef(self.uart.send('cmd,usb2'))
            ack = await self.wait_ack('usb2')
            if ack != 0:
                return
            ret = await self.wait_ret('usb2')
            if ret != 0:
                return
            speed = self.items['usb2'].value
            if speed == '480' or speed == '12':
                self.okay_item('usb2', speed)
                return
            timeout -= 1
            await asyncio.sleep(1)
        print('fail usb2')
        self.fail_item('usb2')

    def init_usb3_items(self):
        items = ['usb3_up_speed', 'usb3_down_speed', 'usb3_up_rw',
                'usb3_down_rw', 'usb3_up_sdx', 'usb3_down_sdx']
        for item in items:
            self.items[item].value = None
            self.items[item].text = None
            self.items[item].ack = None
            self.items[item].okay = None
            self.items[item].update = 1

    @cancelled_exception()
    async def check_usb3(self, timeout):
        self.init_usb3_items()
        res = [self.usb3_speed(usb) for usb in ['usb3_up', 'usb3_down']]
        await asyncio.gather(*res)
        res = [self.usb3_sdx(usb) for usb in ['usb3_up', 'usb3_down']]
        await asyncio.gather(*res)

        self.items['usb3_up_rw'].ack = None
        aef(self.uart.send(f'cmd,usb3_up_rw,file'))
        ack = await self.wait_ack(f'usb3_up_rw')
        if ack != 0:
            return
        ret = await self.wait_ret(f'usb3_up_rw')
        if ret != 0:
            return
        err = self.items['usb3_up_rw'].value
        self.items['usb3_up_rw'].value = None
        if err != '0':
            self.fail_item('usb3_up_rw', 'File error')
            self.fail_item('usb3_up_down', 'File error')
            return

        res = [self.usb3_rw(usb) for usb in ['usb3_up', 'usb3_down']]
        await asyncio.gather(*res)

    @cancelled_exception()
    async def usb3_speed(self, usb):
        self.items[f'{usb}_speed'].ack = None
        aef(self.uart.send(f'cmd,{usb}_speed'))
        ack = await self.wait_ack(f'{usb}_speed')
        if ack != 0:
            return
        ret = await self.wait_ret(f'{usb}_speed')
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
        aef(self.uart.send(f'cmd,{usb}_sdx'))
        ack = await self.wait_ack(f'{usb}_sdx')
        if ack != 0:
            return
        ret = await self.wait_ret(f'{usb}_sdx')
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
        aef(self.uart.send(f'cmd,{usb}_rw,check,{sdx}'))
        ack = await self.wait_ack(f'{usb}_rw')
        if ack != 0:
            return
        ret = await self.wait_ret(f'{usb}_rw')
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
    async def check_switch(self, timeout):
        while timeout >= 0:
            self.items['boot_mode'].ack = None
            aef(self.uart.send('cmd,boot_mode'))
            ack = await self.wait_ack('boot_mode')
            if ack != 0:
                return
            ret = await self.wait_ret('boot_mode', 30)
            if ret != 0:
                return
            boot_mode = self.items['boot_mode'].value
            tmp = '(' + str(timeout) + ')'
            self.ready_item('boot_mode', boot_mode + tmp, 2)
            if boot_mode == 'emmc':
                self.okay_item('boot_mode', boot_mode)
                return
            timeout -= 1
            await asyncio.sleep(1)
        self.fail_item('boot_mode', boot_mode)

    @cancelled_exception()
    async def check_eth_speed(self, timeout):
        while timeout:
            self.items['eth_speed'].ack = None
            aef(self.uart.send('cmd,eth_speed'))
            ack = await self.wait_ack('eth_speed')
            if ack != 0:
                return
            ret = await self.wait_ret('eth_speed', 10)
            if ret != 0:
                return
            speed = self.items['eth_speed'].value
            if speed == '1000':
                self.okay_item('eth_speed', speed)
                return
            timeout -= 2
            await asyncio.sleep(2)
        self.fail_item('eth_speed', self.items['eth_speed'].value)

    @cancelled_exception()
    async def check_usb_fw(self):
        self.items['usb_fw'].ack = None
        aef(self.uart.send('cmd,usb_fw'))
        ack = await self.wait_ack('usb_fw')
        if ack != 0:
            return
        ret = await self.wait_ret('usb_fw', 50)
        if ret != 0:
            return
        ver = self.items['usb_fw'].value
        if ver == '2223':
            self.okay_item('usb_fw', ver)
        else:
            self.fail_item('usb_fw', ver)

    @cancelled_exception()
    async def check_fan(self):
        self.items['fan'].ack = None
        aef(self.uart.send(f'cmd,fan,0'))
        ack = await self.wait_ack('fan')
        if ack != 0:
            return
        ret = await self.wait_ret('fan', 5)
        if ret != 0:
            return
        if self.items['fan'].value != '0':
            self.fail_item('fan')
            return
        pin1, pin2 = [await self.adc.read_pin(pin) for pin in self.fan]
        if pin1 < 4 and pin2 < 1.5:
            self.fail_item('fan')
            return

        self.items['fan'].ack = None
        self.items['fan'].value = None
        aef(self.uart.send(f'cmd,fan,1'))
        ack = await self.wait_ack('fan')
        if ack != 0:
            return
        ret = await self.wait_ret('fan', 5)
        if ret != 0:
            return
        if self.items['fan'].value != '0':
            self.fail_item('fan')
            return
        pin1, pin2 = [await self.adc.read_pin(pin) for pin in self.fan]
        if pin1 < 4 and pin2 > 0.5:
            self.fail_item('fan')
            return
        else:
            self.okay_item('fan')

    @cancelled_exception()
    async def check_gpio_hdmi(self):
        self.ready_item('hdmi', 'Testing...', 2)
        defects = set()

        self.items['hdmi'].ack = None
        aef(self.uart.send(f'cmd,hdmi,0'))
        ack = await self.wait_ack('hdmi')
        if ack != 0:
            return
        ret = await self.wait_ret('hdmi', 5)
        if ret != 0:
            return

        ret = await self.adc.read_pin_hdmi(self.hdmi, 0)
        if ret != 0:
            defects.update(ret)

        self.items['hdmi'].ack = None
        aef(self.uart.send(f'cmd,hdmi,1'))
        ack = await self.wait_ack('hdmi')
        if ack != 0:
            return
        ret = await self.wait_ret('hdmi', 5)
        if ret != 0:
            return

        ret = await self.adc.read_pin_hdmi(self.hdmi, 1)
        if ret != 0:
            defects.update(ret)

        self.items['hdmi'].ack = None
        aef(self.uart.send(f'cmd,hdmi,2'))
        ack = await self.wait_ack('hdmi')
        if ack != 0:
            return
        ret = await self.wait_ret('hdmi', 5)
        if ret != 0:
            return

        ret = await self.adc.read_pin_hdmi(self.hdmi, 2)
        if ret != 0:
            defects.update(ret)
        if len(defects) != 0:
            self.fail_item('hdmi', ' '.join(defects))
            return
        self.okay_item('hdmi', 'OK')


    @cancelled_exception()
    async def check_gpio(self):
        self.ready_item('gpio', 'Testing...', 2)
        defects = set()

        gpios = deepcopy(self.gpios)
        for i in self.items_gpio:
            self.items['gpio'].ack = None
            aef(self.uart.send(f'cmd,gpio,{i}'))
            ack = await self.wait_ack('gpio')
            if ack != 0:
                return
            ret = await self.wait_ret('gpio', 5)
            if ret != 0:
                return
            result = await self.adc.read_times(gpios, i)
            if result != 0:
                self.items_gpio[i].okay = 0
                defects.update(result)
                LOG.error(f'{result}')
                for i in result:
                    for idx, j in enumerate(gpios):
                        if i == j.label:
                            del(gpios[idx])
            elif result == 0:
                self.items_gpio[i].okay = 1
        if all(v.okay for k, v in self.items_gpio.items()):
            self.okay_item('gpio', 'OK')
        else:
            self.fail_item('gpio', ','.join(defects))

    def init_eth_items(self):
        self.items['led_eth'].value = None
        self.items['led_eth'].text = None
        self.items['led_eth'].ack = None
        self.items['led_eth'].okay = None
        self.items['led_eth'].update = 1

    @cancelled_exception()
    async def check_led_eth(self):
        self.init_eth_items()
        self.items['led_eth'].ack = None
        aef(self.uart.send('cmd,led_eth,1000'))
        ack = await self.wait_ack('led_eth')
        if ack != 0:
            return
        ret = await self.wait_ret('led_eth', 15)
        if ret != 0:
            return

        if self.items['led_eth'].value != '0':
            self.fail_item('led_eth')
            return
        ret = await self.adc.check_led_eth(self.led_eth, mode=1000)
        if ret != 0:
            self.fail_item('led_eth')
            return

        self.items['led_eth'].ack = None
        self.items['led_eth'].value = None
        aef(self.uart.send('cmd,led_eth,100'))
        ack = await self.wait_ack('led_eth')
        if ack != 0:
            return
        ret = await self.wait_ret('led_eth', 15)
        if ret != 0:
            return

        if self.items['led_eth'].value != '0':
            self.fail_item('led_eth')
            return
        ret = await self.adc.check_led_eth(self.led_eth, mode=100)
        if ret != 0:
            self.fail_item('led_eth')
            return
        else:
            self.okay_item('led_eth')

    @cancelled_exception()
    async def check_led_sys(self):
        ret = await self.adc.check_led(self.led_pwr, onoff=1)
        if ret == 0:
            self.okay_item('led_pwr')
        else:
            self.fail_item('led_pwr')

        self.items['led_sys'].ack = None
        aef(self.uart.send('cmd,led_sys,0'))
        ack = await self.wait_ack('led_sys')
        if ack != 0:
            return
        ret = await self.wait_ret('led_sys', 10)
        if ret != 0:
            return

        if self.items['led_sys'].value != '0':
            self.fail_item('led_sys')
            return

        ret = await self.adc.check_led(self.led_sys, onoff=0)
        if ret != 0:
            self.fail_item('led_sys')
            return

        self.items['led_sys'].ack = None
        aef(self.uart.send('cmd,led_sys,1'))
        ack = await self.wait_ack('led_sys', 5)
        if ack != 0:
            return
        ret = await self.wait_ret('led_sys', 10)
        if ret != 0:
            return
        if self.items['led_sys'].value != '0':
            self.fail_item('led_sys')
            return

        ret = await self.adc.check_led(self.led_sys, onoff=1)
        if ret != 0:
            self.fail_item('led_sys')
            return
        else:
            self.okay_item('led_sys')

