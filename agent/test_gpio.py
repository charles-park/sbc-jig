from adc import ADC
import asyncio
from gpio import GPIO
import sys

async def read_gpio(adc, argv):
    gpio = GPIO('XU4')
    while True:
        if len(argv) == 2:
            test = await adc.read_pin(gpio.gpios, argv[1])
        #print(await adc._read(0x8, 0xc, "LED_PWR"), await adc._read(0x8, 0x8, "LED_ALIVE"))
        #print(await adc._read(0x19, 0xf, "GREEN"), await adc._read(0x19, 0xb, "YELLO"))
        #print(await adc._read(0x19, 0xe, "SDA"), await adc._read(0x19, 0xa, "SCL") , await adc._read(0x19, 0xd, "CEC"))
        #await adc.read_chip(0x9)
        #res = await adc._read(0x9, 0xe, "VCC5V")
        #res = await adc._read(0x8, 0xc, "VCC5V")
        #print(res)
        await asyncio.sleep(0.2)
        '''
        async for _onoff, vddee in adc.check_pwr(pwrs):
            pass
        '''

async def main(argv):
    adc = ADC(0)
    task0 = await read_gpio(adc, argv)

if __name__ == "__main__":
    asyncio.run(main(sys.argv))
