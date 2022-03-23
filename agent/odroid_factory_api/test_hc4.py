# asyncio unittest example: https://gist.github.com/ly0/b3be4a5b7708a9a8c3da

import unittest
import asyncio
import inspect
import sys

try:
    from . import api
except ImportError:
    import api
try:
    from . import constants
except ImportError:
    import constants


def async_test(function):
    def wrapper(*args, **kwargs):
        if inspect.iscoroutinefunction(function):
            future = function(*args, **kwargs)
        else:
            coroutine = asyncio.coroutine(function)
            future = coroutine(*args, **kwargs)
        asyncio.get_event_loop().run_until_complete(future)
    return wrapper


class TestApi(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(TestApi, self).__init__(*args, **kwargs)
        self.target_board = 'hc4'
        self.api_manager = api.API_MANAGER(
            board=self.target_board,
        )
        self.api_manager.mac_addr = constants.MAC_TABLES_BY_BOARD[self.target_board][0] + '0001'

    @async_test
    async def test_request_mac_and_delete_assigned_sign(self):
        results = await self.api_manager.request_mac_addr()
        print(f'Received UUID: {results}')
        results = await self.api_manager.delete_assigned_sign()
        print(f'Deleted MAC address: {results["receivedData"]["mac_addr"]}')
        self.assertIsNotNone(results)

    @async_test
    async def test_get_criteria(self):
        results = await self.api_manager.get_criteria_for_board()
        self.assertIsNotNone(results)

    @async_test
    async def test_update_uuid_results(self):
        results = await self.api_manager.update_record({
            'uuid': '12345678-1234-1234-1234-123456789012'
        })
        self.assertEqual(results['isUpdated'], True)

    @async_test
    async def test_update_ethernet_results(self):
        results = await self.api_manager.update_record({
            'ethernet_bandwidth': 1000,
            'ethernet_ping': 12.34
        })
        self.assertEqual(results['isUpdated'], True)

    @async_test
    async def test_update_iperf_udp_results(self):
        results = await self.api_manager.update_record({
            'iperf_rx_udp_bandwidth': 999.99,
            'iperf_rx_udp_loss_rate': 99.99
        })
        self.assertEqual(results['isUpdated'], True)

    @async_test
    async def test_update_lspci_results(self):
        results = await self.api_manager.update_record({
            'lspci_sata_recognition': True
        })
        self.assertEqual(results['isUpdated'], True)

    @async_test
    async def test_update_sata0_results(self):
        results = await self.api_manager.update_record({
            'sata0_read_speed': '120.01',
            'sata0_write_speed': '100.99',
            'sata0_file_integrity': -1000
        })
        self.assertEqual(results['isUpdated'], True)

    @async_test
    async def test_update_sata1_results(self):
        results = await self.api_manager.update_record({
            'sata1_read_speed': '120.01',
            'sata1_write_speed': '100.99',
            'sata1_file_integrity': -1000
        })
        self.assertEqual(results['isUpdated'], True)

    @async_test
    async def test_update_usb_results(self):
        results = await self.api_manager.update_record({
            'usb_2_bandwidth': 480,
        })
        self.assertEqual(results['isUpdated'], True)

    @async_test
    async def test_update_led_system_status_results(self):
        results = await self.api_manager.update_record({
            'led_system': True,
            'led_power': False,
            'led_hdd': -1001
        })
        self.assertEqual(results['isUpdated'], True)

    @async_test
    async def test_update_hdmi_status_results(self):
        results = await self.api_manager.update_record({
            'hdmi_edid_sda': -1,
            'hdmi_edid_scl': -2,
            'hdmi_cec': -3,
            'hdmi_hpd': -4,
        })
        self.assertEqual(results['isUpdated'], True)

    @async_test
    async def test_update_power_bus_status_results(self):
        results = await self.api_manager.update_record({
            'power_5v': 5.3,
            'power_3_3v': 3.3,
            'power_vdeee': 0.9
        })
        self.assertEqual(results['isUpdated'], True)

    @async_test
    async def test_update_fan_status_results(self):
        results = await self.api_manager.update_record({
            'fan_pwm': True,
            'fan_tacho': True
        })
        self.assertEqual(results['isUpdated'], True)

    @async_test
    async def test_update_io_header_results(self):
        results = await self.api_manager.update_record({
            'header_5pin_io': True
        })
        self.assertEqual(results['isUpdated'], True)

    @async_test
    async def test_update_all_pass(self):
        results = await self.api_manager.update_record({
            'all_pass': True
        })
        self.assertEqual(results['isUpdated'], True)

if __name__ == '__main__':
    unittest.main()
