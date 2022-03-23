import asyncio
from usb import USB

async def main():
    usb = USB()
    #print(await usb.scan_sata())
    usb.init_node(usb.sata)

if __name__ == "__main__":
    asyncio.run(main())
