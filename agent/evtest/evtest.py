import evdev
from evdev import InputDevice
from evdev import list_devices
import asyncio

class Evtest():
    def __init__(self):
        self.devices = [InputDevice(path) for path in list_devices()]
        self.events = {'hp_det':None, 'ir':None}
        ret = self.get_event_name()
        if ret != 0:
            print('Fail get_event_name')
        self.device_hp = self.events['hp_det']
        self.device_ir = self.events['ir']

    def get_event_name(self):
        cnt = 0
        for idx, dev in enumerate(self.devices):
            if dev.name == 'rockchip,rk809-codec Headphones':
                self.events['hp_det'] = self.devices[idx]
                cnt += 1
            elif dev.name == 'fdd70030.pwm':
                self.events['ir'] = self.devices[idx]
                cnt += 1
        if cnt > 0:
            return 0
        return 1

    async def read_hp_det(self):
        async for event in self.device_hp.async_read_loop():
            if event.type == evdev.ecodes.EV_SW:
                yield event.value

    async def read_ir(self):
        async for event in self.device_ir.async_read_loop():
            #print(evdev.categorize(event))
            #print(evdev.ecodes.EV[event.type])
            if event.type == evdev.ecodes.EV_KEY:
                if event.code == evdev.ecodes.KEY_ENTER:
                    yield 'enter', event.value
                elif event.code == evdev.ecodes.KEY_VOLUMEDOWN:
                    yield 'eth_green', event.value
                elif event.code == evdev.ecodes.KEY_VOLUMEUP:
                    yield 'eth_yellow', event.value
                elif event.code == evdev.ecodes.KEY_HOME:
                    yield 'print', event.value
                elif event.code == evdev.ecodes.KEY_POWER:
                    yield 'poweroff', event.value
                elif event.code == evdev.ecodes.KEY_MENU:
                    yield 'scan', event.value


def main():
    loop = asyncio.get_event_loop()
    ev = Evtest()
    task_uart = asyncio.ensure_future(ev.read_hp_det())

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        pass
        task_uart.cancel()

if __name__ == "__main__":
    main()
