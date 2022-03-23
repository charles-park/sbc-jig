import asyncio
from asyncio import ensure_future as aef
from utils.log import init_logger
from functools import wraps

LOG = init_logger('', testing_mode='info')

class Component():
    def __init__(self, text='None', flag_text=1):
        self.text = text
        self.flag_text = flag_text
        self.ack = None
        self.ret = None
        self.value = None
        self.okay = None
        self.update = None

class Task():
    def __init__(self, func, timeout=0):
        self.func = func
        self.id = None
        self.timeout = timeout

    async def run(self):
        if await self.cancelled() == 0:
            if self.timeout == 0:
                self.id = aef(self.func())
            else:
                self.id = aef(self.func(self.timeout))
            await self.id
            return self.id

    async def cancelled(self):
        try:
            if type(self.id) != asyncio.Task:
                return 0
            if self.id.cancel():
                await self.id
            return 0
        except asyncio.CancelledError:
            if self.id.cancelled():
                LOG.warning(f'cancelled {self.id}')
                return 0
        except Exception as e:
            LOG.warning(f'cancel? {e} {self.id}')

def cancelled_exception():
    def wrapper(fn):
        @wraps(fn)
        async def wrapped(*args, **kwargs):
            try:
                return await fn(*args, **kwargs)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                LOG.error(f"Error {e} {fn.__name__}")
        return wrapped
    return wrapper

