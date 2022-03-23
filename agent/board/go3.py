from gpio import GPIO
import asyncio
from asyncio import ensure_future as aef
from functools import wraps
from utils.log import init_logger
from copy import deepcopy

from task import Component
from task import Task
from task import cancelled_exception

LOG = init_logger('', testing_mode='info')

class GO3():
    def __init__(self):
        self.model = 'GO3'
        self.pins = GPIO(self.model)
        self.pwrs = self.pins.pwrs
        self.keypads = self.pins.keypads
        self.pin10 = self.pins.pin10
        self.led_sys = self.pins.led_sys
        self.led_pwr = self.pins.led_pwr
        self.led_chg = self.pins.led_chg
        self.audio = self.pins.audio
        self.items = None
        self.sw_joystick = False
        self.btns =  ['TL', 'TL2', 'TR', 'TR2','V_DOWN', 'V_UP', 'F1', 'F2']
        self.flag0 = ['finish', 'led_sys', 'led_pwr', 'led_chg']
        self.flag1 = ['uart', 'usb2', 'push_btn', 'pin10', 'joystick',
                'onoff', 'dc']
        self.flag2 = ['hp_det', 'battery', 'audio', 'btn_flashrom', 'keypad']
        self.items0 = {k:Component(flag_text=0) for k in self.flag0 + self.btns}
        self.items1  = {k:Component(flag_text=1) for k in self.flag1}
        self.items2  = {k:Component(flag_text=2) for k in self.flag2}
        self.items = {**self.items0, **self.items1, **self.items2}

        self.labels_keypads = [x.label for x in self.keypads]
        self.items_keypads = {k:Component() for k in self.labels_keypads}
        self.labels_pin10 = [x.label for x in self.pin10]
        self.items_pin10 = {k:Component() for k in self.labels_pin10}

        self.task_usb2 = Task(self.check_usb2, 20)
        self.task_keypad = Task(self.check_keypad)
        self.task_pin10 = Task(self.check_pin10)
        self.task_push_btn = Task(self.check_push_btn, 30)
        self.task_led_sys = Task(self.check_led_sys)
        self.task_led_pwr = Task(self.check_led_pwr)
        self.task_led_chg = Task(self.check_led_chg)
        self.task_audio = Task(self.check_audio)
        self.task_joystick = Task(self.check_joystick)
        self.task_btn_flashrom = Task(self.check_btn_flashrom)
        self.task_battery = Task(self.check_battery)
        self.task_dc = Task(self.check_dc)

    def init_item(self, item):
        for k, v in self.items.items():
            if k == item:
                v.req = v.ack = v.ret = v.seq = v.value = v.okay = v.tmp = None
                if k == 'finish':
                    v.okay = 2
                v.update = 1

    def init_variables(self):
        for k, v in self.items.items():
            if k == 'uart' or k == 'onoff':
                continue
            if k == 'battery':
                v.okay = None
                v.update = 1
                continue
            v.req = v.ack = v.ret = v.seq = v.value = v.okay = v.tmp = None
            if k == 'finish':
                v.okay = 2
            if k == 'hp_det':
                v.tmp = "HP_DET"
            v.update = 1

    async def check_finish(self):
        if self.items['finish'].okay == 2:
            _finish = deepcopy(self.items)
            '''
            for k, v in _finish.items():
                print(k, v.okay)
            '''

            del(_finish['finish'])
            finish1 = any(v.okay == None for k, v in _finish.items())
            finish2 = any(v.okay == 2 for k, v in _finish.items())
            finish = finish1 or finish2
            if finish != False:
                return

            aef(self.uart.send('cmd,finish'))
            err = []
            for k, v in _finish.items():
                if v.okay != 1:
                    err.append(k)
            if len(err) > 0:
                self.fail_items('finish')
                return
            self.okay_items('finish')

    async def monitor_pwr(self):
        uart = None
        onoff = None
        battery = 0
        async for _onoff, bat in self.adc.check_pwr(self.pwrs):
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

            if abs(battery - bat) > 0.01:
                battery = self.items['battery'].tmp = bat
                self.items['battery'].update = 1

            await self.check_finish()

    async def sequence_main(self):
        while True:
            if self.seq_main == 1:
                self.seq_main = 2

                aef(self.task_keypad.run())
                aef(self.task_pin10.run())
                aef(self.task_push_btn.run())
                aef(self.task_led_sys.run())
                aef(self.task_led_pwr.run())
                aef(self.task_led_chg.run())
                aef(self.task_usb2.run())
                aef(self.task_audio.run())
                aef(self.task_joystick.run())
                aef(self.task_btn_flashrom.run())
                aef(self.task_battery.run())
                aef(self.task_dc.run())

            await asyncio.sleep(1)

    @cancelled_exception()
    async def check_usb2(self, timeout):
        count = 0
        while count < timeout:
            self.items['usb2'].ack = None
            aef(self.uart.send('cmd,usb2'))
            ack = await self.wait_ack(self.items['usb2'], 5)
            if ack != 0:
                return
            ret = await self.wait_ret(self.items['usb2'])
            if ret != 0:
                return
            if self.items['usb2'].value == '480':
                self.okay_items('usb2')
                speed = int(self.items['usb2'].value)
                return
            count += 1
            await asyncio.sleep(1)
        self.fail_items('usb2')

    @cancelled_exception()
    async def check_push_btn(self, timeout=30):
        self.items['push_btn'].ack = None
        aef(self.uart.send('cmd,push_btn'))
        ack = await self.wait_ack(self.items['push_btn'], 5)
        if ack != 0:
            for i in self.btns:
                self.fail_items(i)
            self.fail_items('push_btn')
            return
        ret = await self.wait_ret(self.items['push_btn'])
        if ret != 0:
            for i in self.btns:
                self.fail_items(i)
            self.fail_items('push_btn')
            return
        if self.items['push_btn'].value == '0':
            for i in self.btns:
                self.items[i].okay = 2
                self.items[i].update = 1
        if self.items['push_btn'].value != '0':
            for i in self.btns:
                self.items[i].okay = 2
                self.items[i].update = 1
            for i in self.items['push_btn'].tmp:
                self.fail_items(i)
        cnt = 0
        while cnt < timeout*2:
            for i in self.btns:
                if self.items[i].okay == 0:
                    continue
                val = self.items[i].value
                tmp = self.items[i].tmp
                if val == '1' and tmp == '0':
                    self.okay_items(i)
            check = [self.items[i].okay for i in self.btns]
            finish = all(v == 1 for v in check)
            if finish:
                break
            cnt += 1
            await asyncio.sleep(0.5)

        defects = 0
        for i in self.btns:
            if self.items[i].okay != 1:
                self.fail_items(i)
                defects += 1
        if defects == 0:
            self.okay_items('push_btn')
        else:
            self.fail_items('push_btn')

    @cancelled_exception()
    async def check_pin10(self):
        self.ready_items('pin10', "Testing...", None)
        defects = []
        pin10 = deepcopy(self.pin10)
        for i in self.items_pin10:
            self.items['pin10'].ack = None
            aef(self.uart.send(f'cmd,pin10,{i}'))
            ack = await self.wait_ack(self.items['pin10'], 5)
            if ack != 0:
                return
            ret = await self.wait_ret(self.items['pin10'], 5)
            if ret != 0:
                return
            result = await self.adc.read_times(pin10, i)
            if type(result) == list:
                self.items_pin10[i].okay = 0
                defects += result[0]
                LOG.error(f'{result}')
                for i in result:
                    for idx, j in enumerate(pin10):
                        if i == j.label:
                            del(pin10[idx])
            elif result == 0:
                self.items_pin10[i].okay = 1
        if all(v.okay for k, v in self.items_pin10.items()):
            self.okay_items('pin10', "OK")
        else:
            self.fail_items('pin10', ",".join(defects))


    @cancelled_exception()
    async def check_keypad(self):
        self.ready_items('keypad', "Testing...", None)
        defects = []
        keypads = deepcopy(self.keypads)
        for i in self.items_keypads:
            self.items['keypad'].ack = None
            aef(self.uart.send(f'cmd,keypad,{i}'))
            ack = await self.wait_ack(self.items['keypad'], 5)
            if ack != 0:
                return
            ret = await self.wait_ret(self.items['keypad'], 5)
            if ret != 0:
                return
            result = await self.adc.read_times(keypads, i)
            if type(result) == list:
                self.items_keypads[i].okay = 0
                defects += result[0]
                LOG.error(f'{result}')
                for i in result:
                    for idx, j in enumerate(keypads):
                        if i == j.label:
                            del(keypads[idx])
            elif result == 0:
                self.items_keypads[i].okay = 1
        if all(v.okay for k, v in self.items_keypads.items()):
            self.okay_items('keypad', "OK")
        else:
            self.fail_items('keypad', ",".join(defects))

    @cancelled_exception()
    async def check_led_chg(self):
        self.items['led_chg'].ack = None
        aef(self.uart.send('cmd,led_chg,0'))
        ack = await self.wait_ack(self.items['led_chg'], 5)
        if ack != 0:
            return
        ret = await self.wait_ret(self.items['led_chg'], 10)
        if ret != 0:
            return

        ret = await self.adc.check_led(self.led_chg, onoff=0)
        if ret != 0:
            self.fail_items('led_chg')
            return

        self.items['led_chg'].ack = None
        aef(self.uart.send('cmd,led_chg,255'))
        ack = await self.wait_ack(self.items['led_chg'], 5)
        if ack != 0:
            return
        ret = await self.wait_ret(self.items['led_chg'], 10)
        if ret != 0:
            return

        ret = await self.adc.check_led(self.led_chg, onoff=1)
        if ret != 0:
            self.fail_items('led_chg')
            return
        else:
            self.okay_items('led_chg')

    @cancelled_exception()
    async def check_led_pwr(self):
        self.items['led_pwr'].ack = None
        aef(self.uart.send('cmd,led_pwr,0'))
        ack = await self.wait_ack(self.items['led_pwr'], 5)
        if ack != 0:
            return
        ret = await self.wait_ret(self.items['led_pwr'], 10)
        if ret != 0:
            return

        ret = await self.adc.check_led(self.led_pwr, onoff=0)
        if ret != 0:
            self.fail_items('led_pwr')
            return

        self.items['led_pwr'].ack = None
        aef(self.uart.send('cmd,led_pwr,255'))
        ack = await self.wait_ack(self.items['led_pwr'], 5)
        if ack != 0:
            return
        ret = await self.wait_ret(self.items['led_pwr'], 10)
        if ret != 0:
            return

        ret = await self.adc.check_led(self.led_pwr, onoff=1)
        if ret != 0:
            self.fail_items('led_pwr')
            return
        else:
            self.okay_items('led_pwr')

    @cancelled_exception()
    async def check_led_sys(self):
        self.items['led_sys'].ack = None
        aef(self.uart.send('cmd,led_sys,0'))
        ack = await self.wait_ack(self.items['led_sys'], 5)
        if ack != 0:
            return
        ret = await self.wait_ret(self.items['led_sys'], 10)
        if ret != 0:
            return

        ret = await self.adc.check_led(self.led_sys, onoff=0)
        if ret != 0:
            self.fail_items('led_sys')
            return

        self.items['led_sys'].ack = None
        aef(self.uart.send('cmd,led_sys,255'))
        ack = await self.wait_ack(self.items['led_sys'], 5)
        if ack != 0:
            return
        ret = await self.wait_ret(self.items['led_sys'], 10)
        if ret != 0:
            return

        ret = await self.adc.check_led(self.led_sys, onoff=1)
        if ret != 0:
            self.fail_items('led_sys')
            return
        else:
            self.okay_items('led_sys')

    @cancelled_exception()
    async def check_battery(self):
        self.items['battery'].ack = None
        aef(self.uart.send('cmd,battery'))
        ack = await self.wait_ack(self.items['battery'], 5)
        if ack != 0:
            return
        ret = await self.wait_ret(self.items['battery'], 10)
        if ret != 0:
            return

        value = float(self.items['battery'].value)/1000000
        diff = round(value - self.items['battery'].tmp, 3)
        if abs(diff) < 0.2:
            self.okay_items('battery')

    @cancelled_exception()
    async def check_dc(self):
        self.items['dc'].ack = None
        aef(self.uart.send('cmd,dc'))
        ack = await self.wait_ack(self.items['dc'], 5)
        if ack != 0:
            return
        ret = await self.wait_ret(self.items['dc'], 10)
        if ret != 0:
            return
        if self.items['dc'].value == '1':
            self.okay_items('dc', 'OK')
        else:
            self.fail_items('dc')


    @cancelled_exception()
    async def check_btn_flashrom(self):
        self.items['btn_flashrom'].ack = None
        aef(self.uart.send('cmd,btn_flashrom,0'))
        ack = await self.wait_ack(self.items['btn_flashrom'], 5)
        if ack != 0:
            self.fail_items('btn_flashrom', 'FAIL')
            return
        ret = await self.wait_ret(self.items['btn_flashrom'], 10)
        if ret != 0:
            self.fail_items('btn_flashrom', 'FAIL')
            return
        if self.items['btn_flashrom'].value != '0':
            self.fail_items('btn_flashrom')
            return

        self.ready_items('btn_flashrom', 'PUSH')

        self.items['btn_flashrom'].ack = None
        aef(self.uart.send('cmd,btn_flashrom,1'))
        ack = await self.wait_ack(self.items['btn_flashrom'], 5)
        if ack != 0:
            self.fail_items('btn_flashrom', 'FAIL')
            return
        ret = await self.wait_ret(self.items['btn_flashrom'], 30)
        if ret != 0:
            self.fail_items('btn_flashrom', 'FAIL')
            return
        if self.items['btn_flashrom'].value != '0':
            self.fail_items('btn_flashrom', 'FAIL')
            return
        else:
            self.okay_items('btn_flashrom', 'OK')

    @cancelled_exception()
    async def check_joystick(self):
        self.items['joystick'].ack = None
        '''
        no joystick
        0.441V, 1.358V

        with joystick
        0.816V, 0.69V

        '''

        tolerance = 15
        t_low = 1-(tolerance/100)
        t_high = 1+(tolerance/100)
        value_adc = [1.2, 0.39, 1.2, 0.39]
        #value_adc_joystick = [0.816, 0.69, 0.816, 0.69]
        value_adc_joystick = [0.74, 0.74, 0.74, 0.74]
        adc = value_adc_joystick if self.sw_joystick else value_adc

        for i in range(3):
            defects = []
            self.ready_items('joystick', 'Testing...', None)
            aef(self.uart.send('cmd,joystick,0'))
            ack = await self.wait_ack(self.items['joystick'], 5)
            if ack != 0:
                return
            ret = await self.wait_ret(self.items['joystick'], 10)
            if ret != 0:
                return

            value = float(self.items['joystick'].value)
            if value < adc[0]*t_low or value > adc[0]*t_high:
                #defects += ["0"]
                defects += ["Right4"]
                LOG.error("FAIL channel0")
            LOG.info(f"channel0 {value}")

            aef(self.uart.send('cmd,joystick,1'))
            ack = await self.wait_ack(self.items['joystick'], 5)
            if ack != 0:
                return
            ret = await self.wait_ret(self.items['joystick'], 10)
            if ret != 0:
                return

            value = float(self.items['joystick'].value)
            if value < adc[1]*t_low or value > adc[1]*t_high:
                defects += ["Right5"]
                LOG.error("FAIL channel1")
            LOG.info(f"channel1 {value}")

            aef(self.uart.send('cmd,joystick,2'))
            ack = await self.wait_ack(self.items['joystick'], 5)
            if ack != 0:
                return
            ret = await self.wait_ret(self.items['joystick'], 10)
            if ret != 0:
                return

            value = float(self.items['joystick'].value)
            if value < adc[2]*t_low or value > adc[2]*t_high:
                defects += ["Left4"]
                LOG.error("FAIL channel2")
            LOG.info(f"channel2 {value}")

            aef(self.uart.send('cmd,joystick,3'))
            ack = await self.wait_ack(self.items['joystick'], 5)
            if ack != 0:
                return
            ret = await self.wait_ret(self.items['joystick'], 10)
            if ret != 0:
                return

            value = float(self.items['joystick'].value)
            if value < adc[3]*t_low or value > adc[3]*t_high:
                defects += ["Left5"]
                LOG.error("FAIL channel3")
            LOG.info(f"channel3 {value}")

            if len(defects) > 0:
                self.fail_items('joystick', ",".join(defects))
            else:
                self.okay_items('joystick', 'OK')
                return

    @cancelled_exception()
    async def check_audio(self):
        self.ready_items('audio', 'Testing...', None)
        set_defects = []
        self.items['audio'].ack = None
        aef(self.uart.send('cmd,audio,0'))
        ack = await self.wait_ack(self.items['audio'], 5)
        if ack != 0:
            self.fail_items('hp_det', 'HP_DET')
            return
        ret = await self.wait_ret(self.items['audio'], 10)
        if ret != 0:
            self.fail_items('hp_det', 'HP_DET')
            return
        ret, defects = await self.adc.check_off_spk_hp(self.audio)
        if ret != 0:
            set_defects += defects
            LOG.error("OFF PATH Failed")

        self.items['audio'].ack = None
        aef(self.uart.send('cmd,audio,1'))
        ack = await self.wait_ack(self.items['audio'], 5)
        if ack != 0:
            self.fail_items('hp_det', 'HP_DET')
            return
        ret = await self.wait_ret(self.items['audio'], 10)
        if ret != 0:
            self.fail_items('hp_det', 'HP_DET')
            return
        ret, defects = await self.adc.check_on_hp(self.audio)
        if ret != 0:
            set_defects += defects
            LOG.error("HP PATH Failed")

        self.items['audio'].ack = None
        aef(self.uart.send('cmd,audio,2'))
        ack = await self.wait_ack(self.items['audio'], 5)
        if ack != 0:
            self.fail_items('hp_det', 'HP_DET')
            return
        ret = await self.wait_ret(self.items['audio'], 10)
        if ret != 0:
            self.fail_items('hp_det', 'HP_DET')
            return
        ret, defects = await self.adc.check_on_spk(self.audio)
        if ret != 0:
            set_defects += defects
            LOG.error("SPK PATH Failed")

        self.items['audio'].ack = None
        aef(self.uart.send('cmd,audio,3'))
        ack = await self.wait_ack(self.items['audio'], 5)
        if ack != 0:
            self.fail_items('hp_det', 'HP_DET')
            return
        ret = await self.wait_ret(self.items['audio'], 10)
        if ret != 0:
            self.fail_items('hp_det', 'HP_DET')
            return
        ret, defects = await self.adc.check_on_spk_hp(self.audio)
        if ret != 0:
            set_defects += defects
            LOG.error("SPK_HP PATH Failed")

        if len(set_defects) > 0:
            tmp = set(set_defects)
            self.fail_items('audio', ",".join(tmp))
        else:
            self.okay_items('audio', 'OK')

        self.ready_items('hp_det', 'OUT')
        self.items['hp_det'].ack = None
        aef(self.uart.send('cmd,hp_det,1'))
        ack = await self.wait_ack(self.items['hp_det'], 5)
        if ack != 0:
            self.fail_items('hp_det', 'HP_DET')
            return
        ret = await self.wait_ret(self.items['hp_det'], 20)
        if ret != 0:
            self.fail_items('hp_det', 'HP_DET')
            return
        if self.items['hp_det'].value != '1':
            self.fail_items('hp_det', 'HP_DET')
            return
        self.ready_items('hp_det', 'IN')

        self.items['hp_det'].ack = None
        aef(self.uart.send('cmd,hp_det,0'))
        ack = await self.wait_ack(self.items['hp_det'], 5)
        if ack != 0:
            self.fail_items('hp_det', 'HP_DET')
            return
        ret = await self.wait_ret(self.items['hp_det'], 20)
        if ret != 0:
            self.fail_items('hp_det', 'HP_DET')
            return
        if self.items['hp_det'].value != '0':
            self.fail_items('hp_det', 'HP_DET')
        else:
            self.okay_items('hp_det', 'HP_DET')
