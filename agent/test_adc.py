from adc import ADC
import asyncio
from gpio import GPIO

async def read_gpio(adc):
    while True:
        #test = await adc.read_pin(gpio.pins, "GPIOAO_14")
        #print(await adc._read(0x8, 0xc, "LED_PWR"), await adc._read(0x8, 0x8, "LED_ALIVE"))
        #print(await adc._read(0x19, 0xf, "GREEN"), await adc._read(0x19, 0xb, "YELLO"))
        #print(await adc._read(0x19, 0xe, "SDA"), await adc._read(0x19, 0xa, "SCL") , await adc._read(0x19, 0xd, "CEC"))
        #await adc.read_chip(0x8)
        #fan
        print(await adc._read(0x18, 0xb, "vcc"))
        print(await adc._read(0x18, 0xf, "gnd"))
        #eth_led
        #yellow = await adc._read(0x19, 0x9, "YELLOW")
        #green = await adc._read(0x19, 0xd, "GREEN")
        #print(yellow, green)
        #print(await adc._read(0x19, 0x8, "SYS"))
        #print(await adc._read(0x19, 0xc, "PWR"))
        await asyncio.sleep(0.2)
        '''
        async for _onoff, vddee in adc.check_pwr(pwrs):
            pass
        '''

def main():
    loop = asyncio.get_event_loop()
    adc = ADC(1)
    task0 = asyncio.ensure_future(read_gpio(adc))

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        task0.cancel()

if __name__ == "__main__":
    main()
