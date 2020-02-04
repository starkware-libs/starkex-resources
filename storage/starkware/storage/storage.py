
import asyncio
from abc import ABC, abstractmethod
from importlib import import_module
from typing import Awaitable, Callable, Dict, Optional, Sequence, Tuple, Type, TypeVar

HASH_BYTES = 32


class Storage(ABC):
    """
    This is a base storage class, all storage classes should inherit from it.
    """

    @staticmethod
    async def from_config(config, logger=None) -> 'Storage':
        """
        Creates a Storage instance from a config dictionary.
        """

        parts = config['class'].rsplit('.', 1)
        storage_class = getattr(import_module(parts[0]), parts[1])
        return storage_class(**config['config'])

    @abstractmethod
    async def set_value(self, key: bytes, value: bytes):
        pass

    @abstractmethod
    async def get_value(self, key: bytes) -> Optional[bytes]:
        pass

    @abstractmethod
    async def del_value(self, key: bytes):
        pass

    async def mset(self, updates: Dict[bytes, bytes]):
        await asyncio.gather(*(self.set_value(*item) for item in updates.items()))

    async def mget(self, keys: Sequence[bytes]) -> Tuple[Optional[bytes], ...]:
        return await asyncio.gather(*(self.get_value(key) for key in keys))

    async def set_int(self, key: bytes, value: int):
        value_bytes = str(value).encode('ascii')
        await self.set_value(key, value_bytes)

    async def setnx_int(self, key: bytes, value: int) -> bool:
        value_bytes = str(value).encode('ascii')
        return await self.setnx_value(key, value_bytes)

    async def get_int(self, key: bytes, default=None) -> Optional[int]:
        result = await self.get_value(key)
        return default if result is None else int(result)

    async def set_str(self, key: bytes, value: str):
        value_bytes = value.encode('ascii')
        await self.set_value(key, value_bytes)

    async def get_str(self, key: bytes, default=None) -> Optional[str]:
        result = await self.get_value(key)
        return default if result is None else result.decode('ascii')

    async def setnx_value(self, key: bytes, value: bytes) -> bool:
        raise NotImplementedError(f'{self.__class__.__name__} does not implement setnx_value')

    async def get_storage_data(self, mode: Optional[str]) -> str:
        raise NotImplementedError(f'{self.__class__.__name__} does not implement get_storage_data')


TDBObject = TypeVar('TDBObject', bound='DBObject')


class DBObject(ABC):
    @abstractmethod
    def serialize(self) -> bytes:
        pass

    @classmethod
    def deserialize(cls: Type[TDBObject], data: bytes) -> TDBObject:
        raise NotImplementedError()

    @classmethod
    def prefix(cls) -> bytes:
        """
        Prefix for the keys in the database.
        """
        raise NotImplementedError()

    @classmethod
    def db_key(cls, suffix: bytes) -> bytes:
        return cls.prefix() + b':' + suffix

    @classmethod
    async def get(cls: Type[TDBObject], storage: Storage, suffix: bytes) -> Optional[TDBObject]:
        res = await storage.get_value(cls.db_key(suffix))
        if res is None:
            return None
        return cls.deserialize(res)

    async def set(self, storage: Storage, suffix: bytes):
        await storage.set_value(self.db_key(suffix), self.serialize())

    async def setnx(self, storage: Storage, suffix: bytes) -> bool:
        return await storage.setnx_value(self.db_key(suffix), self.serialize())


class Fact(DBObject):
    """
    A fact is a DB object with a DB key that is a hash of its value.
    Use set_fact() and get() to read and write facts.
    """
    @abstractmethod
    async def _hash(self, hash_func: Callable[[bytes, bytes], Awaitable[bytes]]) -> bytes:
        pass

    async def set_fact(
            self, storage: Storage, hash_func: Callable[[bytes, bytes], Awaitable[bytes]]) -> bytes:
        hash_val = await self._hash(hash_func)
        await DBObject.set(self, storage, hash_val)
        return hash_val


class LockError(Exception):
    pass


class LockObject(ABC):
    @abstractmethod
    async def extend(self):
        pass


class LockManager(ABC):
    @abstractmethod
    async def lock(self, name: str) -> LockObject:
        pass
