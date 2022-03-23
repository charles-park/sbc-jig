import sys
import asyncio
from asyncio import ensure_future as aef
from uart import Uart

USB_R_U = '1.2'
USB_R_D = '1.3'
PORT_UART = [USB_R_U, USB_R_D]

async def main(argv):
    uart = Uart(model='XU4')
    task = aef(uart.available_uart())
    if len(argv) == 2:
        await uart.send(argv[1])
    else:
        await uart.send('hello, world')

if __name__ == "__main__":
    asyncio.run(main(sys.argv))
