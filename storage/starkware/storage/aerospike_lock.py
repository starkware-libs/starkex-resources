import asyncio
import logging
import random
import time
from typing import List, Tuple

import aerospike
from aerospike import exception as ex

from .storage import LockError, LockManager, LockObject

logger = logging.getLogger(__name__)


class AerospikeLockObject(LockObject):
    def __init__(self, lock_manager: 'AerospikeLockManager', name: str):
        self.lock_manager = lock_manager
        self.name = name

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.lock_manager._unlock(self.name)

    async def extend(self):
        await self.lock_manager._extend(self.name)


class AerospikeLockManager(LockManager):
    def __init__(self, hosts: List[Tuple[str, int]],
                 namespace: str = 'starkpoc',
                 aero_set: str = 'stark_ex',
                 use_services_alternate: bool = False,
                 ttl: int = 30,
                 n_retries: int = 30,
                 max_wait_time: float = 1.):
        self.aero_set = aero_set
        self.namespace = namespace
        self.ttl = ttl
        self.n_retries = n_retries
        self.max_wait_time = max_wait_time
        while True:
            try:
                self.client = aerospike.client({
                    'hosts': hosts,
                    'use_services_alternate': use_services_alternate
                }).connect()
                logger.info(
                    f'Aerospike client is ready, nodes in cluster: {self.client.get_nodes()}')
                break
            except aerospike.exception.ClientError:
                logger.warning(f'Aerospike lock not ready, will try again in 1 sec', exc_info=True)
                time.sleep(1)

    async def try_lock(self, name: str) -> AerospikeLockObject:
        try:
            self.client.put(
                (self.namespace, self.aero_set, name),
                {'value': '1'},
                policy={'exists': aerospike.POLICY_EXISTS_CREATE},
                meta={'ttl': self.ttl},
            )
            return AerospikeLockObject(self, name)
        except (ex.RecordGenerationError, ex.RecordExistsError) as e:
            raise LockError(e)

    async def lock(self, name: str) -> AerospikeLockObject:
        for _ in range(self.n_retries):
            try:
                return await self.try_lock(name)
            except LockError:
                await asyncio.sleep(random.random() * self.max_wait_time)
        raise LockError()

    async def _extend(self, name: str):
        self.client.touch(
            (self.namespace, self.aero_set, name),
            self.ttl,
        )

    async def _unlock(self, name: str):
        self.client.remove((self.namespace, self.aero_set, name))

    async def destroy(self):
        self.client.close()
