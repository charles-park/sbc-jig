# asyncio unittest example: https://gist.github.com/ly0/b3be4a5b7708a9a8c3da

import unittest
import asyncio
import inspect

from datetime import datetime, timedelta
from pytz import timezone

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

        # For example, this assumes that it requests the count number for Odroid-N2.
        self.target_board = 'n2'
        self.api_manager = api.API_MANAGER(
            board=self.target_board,
        )
        self.api_manager.mac_addr = constants.MAC_TABLES_BY_BOARD[self.target_board][0] + '0001'

    @async_test
    async def test_request_counts_today(self):
        counts = await self.api_manager.get_counts(
            filter='today',
            filter_only_all_pass=False
        )
        self.assertGreaterEqual(counts, 0)

    @async_test
    async def test_request_counts_yesterday(self):
        counts = await self.api_manager.get_counts(
            filter='yesterday',
            filter_only_all_pass=False
        )
        self.assertGreaterEqual(counts, 0)

    @async_test
    async def test_request_counts_this_week(self):
        counts = await self.api_manager.get_counts(
            filter='this_week',
            filter_only_all_pass=False
        )
        self.assertGreaterEqual(counts, 0)

    @async_test
    async def test_request_counts_this_month(self):
        counts = await self.api_manager.get_counts(
            filter='this_month',
            filter_only_all_pass=False
        )
        self.assertGreaterEqual(counts, 0)

    @async_test
    async def test_request_counts_this_year(self):
        counts = await self.api_manager.get_counts(
            filter='this_year',
            filter_only_all_pass=False
        )
        self.assertGreaterEqual(counts, 0)

    @async_test
    async def test_request_counts_from_a_week_ago(self):
        counts = await self.api_manager.get_counts(
            filter='from_a_week_ago',
            filter_only_all_pass=False
        )
        self.assertGreaterEqual(counts, 0)

if __name__ == '__main__':
    unittest.main()
