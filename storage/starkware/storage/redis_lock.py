
import aioredlock

from .storage import LockError, LockManager, LockObject


class RedisLockObject(LockObject):
    def __init__(self, lock_manager: 'RedisLockManager', lock: aioredlock.Lock):
        self.lock_manager = lock_manager
        self.lock = lock

    async def __aenter__(self):
        try:
            return await self.lock.__aenter__()
        except aioredlock.LockError:
            raise LockError()

    async def __aexit__(self, exc_type, exc, tb):
        try:
            await self.lock.__aexit__(exc_type, exc, tb)
        except aioredlock.LockError:
            raise LockError()

    async def extend(self):
        await self.lock_manager.aiored_lock.extend(self.lock)


class RedisLockManager(LockManager):
    def __init__(self, redis_host: str, redis_port: str, lock_timeout: int = 60):
        self.aiored_lock = \
            aioredlock.Aioredlock([(redis_host, redis_port)], lock_timeout=lock_timeout)

    async def lock(self, name: str) -> RedisLockObject:
        try:
            lock = await self.aiored_lock.lock(name)
            return RedisLockObject(self, lock)
        except aioredlock.LockError:
            raise LockError()
