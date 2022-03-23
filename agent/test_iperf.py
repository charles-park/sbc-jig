import asyncio
import iperf

async def main():
    await iperf.is_iperf3_exist()
    #ret_iperf = await asyncio.wait_for(iperf.iperf_udp('192.168.30.11', 1), timeout=30)
    #print(ret_iperf)

if __name__ == "__main__":
    asyncio.run(main())
