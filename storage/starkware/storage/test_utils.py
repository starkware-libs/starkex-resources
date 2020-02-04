import asyncio
import hashlib
from contextlib import contextmanager
from typing import Optional

from .storage import HASH_BYTES, LockManager, LockObject, Storage


async def hash_func(left, right):
    assert len(left) == HASH_BYTES
    assert len(right) == HASH_BYTES
    return hashlib.sha256(left + right).digest()


class DummyLockObject(LockObject):
    def __init__(self, lock_manager, name):
        self.lock_manager = lock_manager
        self.name = name

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.lock_manager.unlock(self.name)

    async def extend(self):
        pass


class DummyLockManager(LockManager):
    def __init__(self):
        self.locked = {}

    async def lock(self, name: str) -> DummyLockObject:
        while name in self.locked:
            await self.locked[name]
        future: asyncio.Future = asyncio.Future()
        self.locked[name] = future
        return DummyLockObject(self, name)

    async def unlock(self, name):
        self.locked[name].set_result(True)
        del self.locked[name]


class BrokenDummyLockManager(LockManager):
    """
    A lock manager that does not lock anything
    """

    def __init__(self):
        self.locked = {}

    async def lock(self, name: str) -> DummyLockObject:
        return DummyLockObject(self, name)

    async def unlock(self, name):
        pass


class MockStorage(Storage):
    """
    Mock storage used for testing.
    """

    def __init__(self):
        self.db = {}

    async def set_value(self, key: bytes, value: bytes):
        assert isinstance(key, bytes)
        assert isinstance(value, bytes)
        self.db[key] = value

    async def setnx_int(self, key: bytes, value: int) -> bool:
        assert isinstance(key, bytes)
        assert isinstance(value, int)
        return await super().setnx_int(key, value)

    async def setnx_value(self, key: bytes, value: bytes) -> bool:
        assert isinstance(key, bytes)
        assert isinstance(value, bytes)
        if self.db.get(key, None) is None:
            self.db[key] = value
            return True
        return False

    async def get_value(self, key: bytes) -> Optional[bytes]:
        assert isinstance(key, bytes)
        return self.db.get(key, None)

    async def del_value(self, key: bytes):
        assert isinstance(key, bytes)
        try:
            del self.db[key]
        except KeyError:
            pass

    async def set_int(self, key: bytes, value: int):
        assert isinstance(key, bytes)
        assert isinstance(value, int)
        await super().set_int(key, value)

    async def get_int(self, key: bytes, default=None) -> Optional[int]:
        assert isinstance(key, bytes)
        return await super().get_int(key, default)

    async def set_str(self, key: bytes, value: str):
        assert isinstance(key, bytes)
        assert isinstance(value, str)
        await super().set_str(key, value)

    async def get_str(self, key: bytes, default=None) -> Optional[str]:
        assert isinstance(key, bytes)
        return await super().get_str(key, default)


class DelayedStorage(Storage):
    """
    Mock storage used for testing async.
    It has a specified selay for each operation.
    """

    def __init__(self, read_delay, write_delay):
        self.read_delay = read_delay
        self.write_delay = write_delay
        self.storage = MockStorage()

    async def set_value(self, key: bytes, value: bytes):
        await asyncio.sleep(self.write_delay)
        await self.storage.set_value(key, value)

    async def setnx_value(self, key: bytes, value: bytes) -> bool:
        await asyncio.sleep(self.write_delay)
        return await self.storage.setnx_value(key, value)

    async def get_value(self, key: bytes) -> Optional[bytes]:
        await asyncio.sleep(self.read_delay)
        return await self.storage.get_value(key)

    async def del_value(self, key: bytes):
        await asyncio.sleep(self.write_delay)
        await self.storage.del_value(key)


def check_time(t0, min_t, max_t):
    """
    Assuming t0 is the start time, checks the current time, and that it does not exceeds the
    given boundaries.
    """
    t1 = asyncio.get_event_loop().time()
    delta = t1 - t0
    assert min_t <= delta <= max_t, \
        'Timing test failed'


@contextmanager
def timed_call_range(min_t=0, max_t=2**20):
    """
    Context manager that asserts the code within took some amount of time, between
    min_t and max_t.

    Example:
    with timed_call(2.9, 3.1):
        time.sleep(3)
    """
    t0 = asyncio.get_event_loop().time()
    yield
    check_time(t0, min_t, max_t)


@contextmanager
def timed_call(expected, epsilon=0.1):
    """
    Context manager that asserts the code within took some amount of time, between
    expected-epsilon and expected+epsilon.

    Example:
    with timed_call(3):
        time.sleep(3)
    """
    t0 = asyncio.get_event_loop().time()
    yield
    check_time(t0, expected - epsilon, expected + epsilon)
