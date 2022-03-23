from asyncio import get_event_loop
from shutil import which
from .constants import *
import asyncio

async def is_iperf3_exist():
    if which('iperf3') is None:
        print("iperf3 is not exist")
        return False
    else:
        cmd = "iperf3 --version"
        proc = await asyncio.create_subprocess_shell(cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()
        if stdout != b'':
            if stdout.split()[1] == b'3.1.3':
                return True
            else:
                print("iperf3 version is not 3.1.3!!")
    return False

async def control_external_iperf_server(ip, message, port=8888):
    loop = get_event_loop()
    try:
        reader, writer = await asyncio.open_connection(
            host=ip, port=port, loop=loop)
        if message == 'bind':
            return True

        writer.write(message.encode())
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    except Exception as err:
        print(err)

async def iperf_udp(ipaddr, ropt):
    if await is_iperf3_exist() == False:
        return False
    await control_external_iperf_server(ipaddr, MSG_IPERF_START)
    await asyncio.sleep(2)

    cmd = f"taskset -c 3 iperf3 -c {ipaddr} -t 10 -u -b 1000m"
    if ropt == 1:
        cmd += " -R"
    proc = await asyncio.create_subprocess_shell(cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    results = stdout.decode('utf-8').rstrip()
    iperf_output_lines = results.split('\n')
    result_line = None
    for idx, line in enumerate(iperf_output_lines):
        if 'Jitter' in line:
            result_line = iperf_output_lines[idx+1]
            break

    await control_external_iperf_server(ipaddr, MSG_IPERF_STOP)

    if result_line is None:
        return None

    tmp = result_line.split('  ')
    #bandwidth = tmp[-4].replace('bits/sec', '').replace(' ', '') + 'b/s'
    bandwidth = tmp[-4].replace('bits/sec', '') + 'b/s'
    loss = tmp[-2].split(' ')[1][1:-1]
    return bandwidth + ',' + loss

def parse_iperf_udp(results):
    try:
        return_results = {
            'bandwidth': 0,
            'loss_rate': 0,
        }

        if 'error' in results:
            return None, None
        else:
            iperf_output_lines = results.split('\n')

        print(iperf_output_lines)
        result_line = None
        for idx, line in enumerate(iperf_output_lines):
            if 'Sent' in line and 'datagrams' in line:
                result_line = iperf_output_lines[idx - 1]
                break

        if result_line is None:
            return None, None

        bandwidth_assist_index = result_line.index('bits/sec')
        lr_ast_after_ms = result_line.split('ms')[1]

        return_results['bandwidth'] = round(
            float(result_line[bandwidth_assist_index - 7:bandwidth_assist_index].strip()[:-2]), 2)

        lr_ast_split_slash = lr_ast_after_ms.split('/')
        lr_ast_split_open = lr_ast_split_slash[1].split('(')

        lost_rate_left = int(lr_ast_split_slash[0].strip())
        lost_rate_right = int(lr_ast_split_open[0].strip())

        if lost_rate_left == 0:
            return_results['loss_rate'] = 0
        else:
            return_results['loss_rate'] = round(
                lost_rate_left / lost_rate_right * 100, 2)
        return return_results

    except exception as e:
        print('parse iperf exception {}'.format(e))
        return None, None

async def main():
    await asyncio.wait_for(iperf_udp('192.168.30.7'))

if __name__ == "__main__":
    asyncio.run(main())
