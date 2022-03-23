import asyncio
from adc import ADC
from gpio import GPIO




async def _main(stdscr, adc):
    # Clear screen
    stdscr.clear()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_YELLOW, -1)
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLUE)
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)

    slaves = [0x8, 0x9, 0xa, 0xb, 0x18, 0x19]
    ch = [0xf, 0xb, 0xe, 0xa, 0xd, 0x9, 0xc, 0x8]
    pad = []
    while True:
        for idx, addr in enumerate(slaves):
            pad.append(curses.newpad(3, 40))
            pad[idx].addstr(0, 0, str(addr))
            pad[idx].addstr(1, 0, '0xf  0xb  0xe  0xa  0xd  0x9  0xc  0x8')
            for i in range(8):
                value = await adc._read(addr, ch[i], i)
                if value[1] < 0.2:
                    pad[idx].addstr(2, i*5, str(value[1]), curses.color_pair(3))
                elif value[1] > 2.8:
                    pad[idx].addstr(2, i*5, str(value[1]), curses.color_pair(2))
                else:
                    pad[idx].addstr(2, i*5, str(value[1]), curses.color_pair(1))
                pad[idx].refresh(0, 0, idx*4 + 5, 5, 35, 73)
        await asyncio.sleep(0.1)
    '''
    for y in range(0, 99):
        for x in range(0, 99):
            pad.addch(y, x, ord('a') + (x*x + y*y) % 26)
    #pad.refresh(0, 0, 5, 5, 20, 75)
    '''
    #stdscr.getkey()
    await asyncio.sleep(1)

model = 'GO3'
pins = GPIO(model)
pwrs = pins.pwrs
keypads = pins.keypads
pin10 = pins.pin10
led_sys = pins.led_sys
led_pwr = pins.led_pwr
led_chg = pins.led_chg
audio = pins.audio
async def main():
    adc = ADC(1)
    while True:
        #ret = await adc.is_on_hp(audio['hp_l'])
        #ret = await adc.is_on_hp(audio['hp_r'])
        ret = await adc.is_off_hp(audio['hp_l'])
        ret = await adc.is_off_hp(audio['hp_r'])

        #ret = await adc.is_on_spk(audio['spk_l'])
        #ret = await adc.is_on_spk(audio['spk_r'])
        #ret = await adc.is_off_spk(audio['spk_l'])
        #ret = await adc.is_off_spk(audio['spk_r'])

if __name__ == "__main__":
    asyncio.run(main())
