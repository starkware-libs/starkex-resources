from typing import Optional

from cachetools import LRUCache

from .storage import Storage


class DictStorage(Storage):
    """
    Local storage using dict.
    """

    def __init__(self, db=None):
        if db is None:
            db = {}
        self.db = db

    async def set_value(self, key: bytes, value: bytes):
        self.db[key] = value

    async def get_value(self, key: bytes) -> Optional[bytes]:
        return self.db.get(key, None)

    async def del_value(self, key: bytes):
        try:
            del self.db[key]
        except KeyError:
            pass


class CachedStorage(Storage):
    def __init__(self, storage: Storage, max_size):
        self.storage = storage
        self.cache = LRUCache(max_size)

    async def set_value(self, key: bytes, value: bytes):
        self.cache[key] = value
        await self.storage.set_value(key, value)

    async def get_value(self, key: bytes) -> Optional[bytes]:
        if key in self.cache:
            return self.cache[key]
        value = await self.storage.get_value(key)
        if value is None:
            return None
        self.cache[key] = value
        return value

    async def del_value(self, key: bytes):
        raise NotImplementedError('CachedStorage is expected to handle only immutable items')
