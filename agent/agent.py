from odroid_factory_api import API_MANAGER
from utils.log import init_logger
import asyncio
from asyncio import ensure_future as aef
from board import M1
from copy import deepcopy
import sys, os, time
import cups
from datetime import datetime
from pytz import timezone
import psutil

p = psutil.Process()
p.cpu_affinity([1])

LOG = init_logger('', testing_mode='info')

from kivy.uix.boxlayout import BoxLayout
from kivy.app import App
from kivy.config import Config
from kivy.properties import ObjectProperty
from kivy.lang import Builder

Config.set('graphics', 'fullscreen', 'auto')
Config.set('graphics', 'borderless', 0)
Config.set('graphics', 'allow_screensaver', 0)

os.environ['DISPLAY'] = ":0.0"

FORUM = 'forum.odroid.com'

BOARD = 'm1'
UI_KV = f'{BOARD}.kv'


class AgentApp(App):
    def build(self):
        Builder.load_file(UI_KV)
        av = AgentView()
        aef(av.init())
        return av

    def app_func(self):
        async def run_wrapper():
            await self.async_run(async_lib='asyncio')
        return asyncio.gather(run_wrapper())

class AgentView(BoxLayout):
    async def init(self):
        self.agent = Agent()
        await self.agent.init_tasks()
        self.ids['ch0'].name.text = f'M1'
        self.ids['ch0'].init(self.agent)
        aef(self.update(self.ids[f'ch0']))

        aef(self.monitor_ip())
        #aef(self.monitor_counts())
        aef(self.monitor_dates())

    async def update(self, channel):
        while True:
            channel.update()
            await asyncio.sleep(0.3)

    async def monitor_dates(self):
        while True:
            x = datetime.now(timezone('Asia/Seoul'))
            self.ids['date'].text = x.strftime("%Y-%m-%d %H:%M")
            await asyncio.sleep(2)

    async def monitor_counts(self):
        api_manager = API_MANAGER(board=BOARD)
        while True:
            cnt = await api_manager.get_counts(
                    filter='today')
            self.ids['cnt_today'].text = str(cnt)
            await asyncio.sleep(10)

    async def monitor_ip(self):
        ipaddr = None
        while True:
            _ipaddr = await self.get_ipaddr()
            if ipaddr != _ipaddr:
                ipaddr = _ipaddr
                if ipaddr.startswith('192.168'):
                    self.ids['ipaddr'].background_color = (0, 1, 0, 0.8)
                else:
                    self.ids['ipaddr'].background_color = (1, 0, 0, 0.8)
                self.ids['ipaddr'].text = ipaddr
            await asyncio.sleep(5)

    async def get_ipaddr(self):
        ipaddr = None
        cmd = 'hostname -I'
        proc = await asyncio.create_subprocess_shell(cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()
        if stderr != b'':
            LOG.error(stderr)
        return stdout.decode('utf-8').rstrip()

class Channel(BoxLayout):
    def __init__(self, **kwargs):
        self.agent = None
        self.items = None
        super(Channel, self).__init__(**kwargs)

    def on_focus(self, instance, value):
        if value == True:
            self.agent.items['ipaddr_printer'].text = ""
            self.agent.items['ipaddr_printer'].update = 1
        elif value == False:
            aef(self.agent.check_printer())

    def on_enter(self, instance):
        try:
            ipaddr = self.ids['ipaddr_printer'].text
            tmp0 = ipaddr.split(".")
            if len(tmp0) != 4:
                print('enter a vaild ipaddr')
                raise
            if int(tmp0[0]) < 0 or int(tmp0[0]) > 255:
                print('enter a vaild ipaddr')
                raise
            if int(tmp0[1]) < 0 or int(tmp0[1]) > 255:
                print('enter a vaild ipaddr')
                raise
            if int(tmp0[2]) < 0 or int(tmp0[2]) > 255:
                print('enter a vaild ipaddr')
                raise
            if int(tmp0[3]) < 0 or int(tmp0[3]) > 255:
                print('enter a vaild ipaddr')
                raise
            aef(self.agent.set_printer_ip(ipaddr))

        except Exception as e:
            self.ids['ipaddr_printer'].text = "Enter a vaild IP address!"
            self.ids['ipaddr_printer'].background_color = (1, 1, 0, 0.8)
            self.ids['ipaddr_printer'].okay = 2
            self.ids['ipaddr_printer'].update = 1

    def init(self, agent):
        self.agent = agent
        self.items = self.agent.items
        self.ids['ipaddr_printer'].bind(focus=self.on_focus)
        self.ids['ipaddr_printer'].bind(on_text_validate=self.on_enter)

    def draw(self, label):
        self.items[label].update = 0
        if self.items[label].okay == 0:
            self.ids[label].background_color = (1, 0, 0, 0.8)
        elif self.items[label].okay == 1:
            self.ids[label].background_color = (0, 1, 0, 0.8)
        elif self.items[label].okay == 2:
            self.ids[label].background_color = (1, 1, 0, 0.8)
        elif self.items[label].okay == None:
            self.ids[label].background_color = (.2, .4, .7, .9)

        if self.items[label].flag_text == 1:
            self.ids[label].text = str(self.items[label].text)

    def recheck_sata(self):
        self.agent.items['finish'].okay = 2
        aef(self.agent.task_sata.run())

    def scan_iperf_server(self):
        aef(self.agent.task_scan_iperf_server.run())

    def update(self):
        if self.agent.seq_main != 0:
            self.ids['finish'].disabled = 1
            finish = self.agent.items['finish'].okay
            if finish == 1 or finish == 0:
                self.ids['finish'].disabled = 0

        for k, v in self.items.items():
            if v.update == 1:
                self.draw(k)

class Agent(M1):
    def __init__(self, channel=0):
        super().__init__()
        self.channel = channel

        self.time = time.time()

        self.ipaddr = None
        self.power_on = None

        self.seq_main = 1

    def ready_item(self, item, value=None, okay=2):
        if type(item) == str:
            if value != None:
                self.items[item].text = value
            self.items[item].okay = okay
            self.items[item].update = 1

    def fail_item(self, item, value=None):
        if type(item) == str:
            if value != None:
                self.items[item].text = value
            self.items[item].okay = 0
            self.items[item].update = 1
        LOG.info(f'FAIL item {item}')

    def okay_item(self, item, value=None):
        if type(item) == str:
            if value != None:
                self.items[item].text = value
            self.items[item].okay = 1
            self.items[item].update = 1
        LOG.info(f'OK item {item}')

    async def init_tasks(self):
        aef(self.sequence_main())

    async def init_sequence(self):
        self.seq_main = 1
        self.time = time.time()
        self.init_variables()

async def main():
    await AgentApp().app_func()

if __name__ == "__main__":
    asyncio.run(main())
