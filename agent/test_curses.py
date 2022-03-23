from curses import wrapper
import curses
import asyncio
from adc import ADC



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

def main(stdscr):
    adc = ADC(0)
    asyncio.run(_main(stdscr, adc))

if __name__ == "__main__":
    wrapper(main)
