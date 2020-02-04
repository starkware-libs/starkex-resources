import json
import logging
from typing import Dict, Optional, Sequence, Tuple

from aioredis import Redis

from .storage import Storage

logger = logging.getLogger(__name__)

SHORT_MODE_EXCLUDE = ('batch_dispatched:', 'package:')


class RedisStorage(Storage):
    def __init__(self, redis: Redis):
        self.redis = redis

    async def set_value(self, key: bytes, value: bytes):
        await self.redis.set(key, value)

    async def setnx_int(self, key: bytes, value: int) -> bool:
        return True if await self.redis.setnx(key, value) == 1 else False

    async def setnx_value(self, key: bytes, value: bytes) -> bool:
        return True if await self.redis.setnx(key, value) == 1 else False

    async def get_value(self, key: bytes) -> Optional[bytes]:
        return await self.redis.get(key)

    async def del_value(self, key: bytes):
        return await self.redis.delete(key)

    async def mset(self, updates: Dict[bytes, bytes]):
        # Convert dict to list.
        updates_list = sum(updates.items(), ())
        await self.redis.mset(*updates_list)

    async def mget(self, keys: Sequence[bytes]) -> Tuple[Optional[bytes], ...]:
        return await self.redis.mget(*keys)

    async def get_storage_data(self, mode: Optional[str] = 'full') -> str:
        data = {}
        keys_list = await self.redis.keys('*')
        keys_list.sort()
        for item in keys_list:
            # Attempt to decode redis key name (it fails for merkle_nodes).
            item_name = None
            item_type = None
            item_value = None
            try:
                item_name = item.decode('utf-8')
                if mode == 'short':
                    # Mode 'short' - exclude blockchain packages.
                    if item_name.startswith(SHORT_MODE_EXCLUDE):
                        continue
                item_type = (await self.redis.type(item)).decode('utf-8')
                if item_type == 'string':
                    if await self.redis.get(item) is not None:
                        item_value = await self.redis.get(item, encoding='utf-8')
                if item_type == 'hash':
                    if await self.redis.hgetall(item) is not None:
                        item_value = await self.redis.hgetall(item, encoding='utf-8')
                if item_type == 'set':
                    if await self.redis.smembers(item) is not None:
                        item_value = await self.redis.smembers(item, encoding='utf-8')
                if item_type == 'list':
                    item_value = await self.redis.lrange(item, 0, -1, encoding='utf-8')
                data[item_name] = item_value
            except Exception:
                # Some items fail because of decoding issues. This is fine. Just skip them.
                pass
        return json.dumps(data, indent=4, sort_keys=True)
