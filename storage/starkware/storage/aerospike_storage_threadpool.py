import asyncio
import codecs
import hashlib
import json
import logging
import time
from abc import abstractmethod
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Tuple

import aerospike

from .storage import Storage

logger = logging.getLogger(__name__)

SHORT_MODE_EXCLUDE = ('batch_dispatched:', 'package:', 'merkle_node:', 'block:')


def create_client(hosts, use_services_alternate):
    while True:
        try:
            client = aerospike.client({
                'hosts': hosts,
                'use_services_alternate': use_services_alternate
            }).connect()
            logger.info(
                f'Aerospike client is ready, nodes in cluster: {client.get_nodes()}')
            return client
        except aerospike.exception.ClientError:
            logger.warning(
                f'Aerospike client not Ready, will try again in 1 sec', exc_info=True)
            time.sleep(1)


class AerospikeThreadedStorageBase(Storage):
    def __init__(self, hosts: List[Tuple[str, int]], namespace: str,
                 aero_set: str,
                 use_services_alternate: Optional[bool] = None,
                 max_workers: Optional[int] = None,
                 override_write_policy: dict = None):

        if use_services_alternate is None:
            use_services_alternate = False

        if max_workers is None:
            max_workers = 32

        self.aero_set = aero_set
        self.namespace = namespace
        self.client = create_client(hosts, use_services_alternate)
        self.pool = ThreadPoolExecutor(max_workers)
        if override_write_policy is None:
            override_write_policy = {}
        # Default write policy.
        write_policy = dict(
            key=aerospike.POLICY_KEY_SEND,
            max_retries=3,
        )
        write_policy.update(override_write_policy)
        self.setnx_write_policy = dict(exists=aerospike.POLICY_EXISTS_CREATE, **write_policy)
        self.set_write_policy = dict(exists=aerospike.POLICY_EXISTS_IGNORE, **write_policy)

    async def setnx_value(self, key: bytes, value: bytes) -> bool:
        try:
            return await asyncio.get_event_loop().run_in_executor(
                self.pool, self.sync_set, key, value, self.setnx_write_policy)
        except aerospike.exception.RecordExistsError:
            return False

    async def set_value(
            self, key: bytes, value: bytes):
        res = await asyncio.get_event_loop().run_in_executor(
            self.pool, self.sync_set, key, value, self.set_write_policy)

    async def get_value(self, key: bytes) -> Optional[bytes]:
        val = await asyncio.get_event_loop().run_in_executor(
            self.pool, self.sync_get, key)
        return val

    async def del_value(self, key: bytes):
        await asyncio.get_event_loop().run_in_executor(
            self.pool, self.sync_del, key)

    @abstractmethod
    def sync_set(self, key: bytes, value: bytes, write_policy: dict) -> bool:
        pass

    @abstractmethod
    def sync_get(self, key: bytes) -> Optional[bytes]:
        pass

    @abstractmethod
    def sync_del(self, key: bytes) -> bool:
        pass


class AerospikeStorage(AerospikeThreadedStorageBase):
    def __init__(self, hosts: List[Tuple[str, int]], namespace: str,
                 aero_set: str,
                 use_services_alternate: Optional[bool] = None,
                 max_workers: Optional[int] = None):
        super().__init__(hosts, namespace, aero_set, use_services_alternate, max_workers)
        self.num_sets = 0
        self.num_gets = 0
        self.num_deletes = 0

    def sync_set(self, key: bytes, value: bytes, policy: dict) -> bool:
        try:
            self.client.put(
                (self.namespace, self.aero_set, bytearray(key)),
                {'value': bytearray(value)},
                policy=policy)
            self.num_sets += 1
            return True
        except aerospike.exception.RecordExistsError:
            return False

    def sync_get(self, key: bytes) -> Optional[bytes]:
        try:
            _, _, record = self.client.get((self.namespace, self.aero_set, bytearray(key)))
            self.num_gets += 1
        except aerospike.exception.RecordNotFound:
            return None
        return bytes(record['value'])

    def sync_del(self, key: bytes) -> bool:
        try:
            self.client.remove((self.namespace, self.aero_set, bytearray(key)))
            self.num_deletes += 1
            return True
        except aerospike.exception.RecordNotFound:
            return False

    async def dump_stats(self) -> dict:
        return ({'num_sets': self.num_sets,
                 'num_gets': self.num_gets,
                 'num_deletes': self.num_deletes})

    async def get_storage_data(self, mode: Optional[str] = 'full') -> str:
        number_of_records = [0]
        data = {}
        keys_list: list = []

        def add_db_key(record_tuple):
            key = bytes(record_tuple[0][2])
            keys_list.append(key)
            number_of_records[0] = number_of_records[0] + 1
            if number_of_records[0] > 3000:
                return False

        scan = self.client.scan(self.namespace, self.aero_set)
        scan.foreach(add_db_key)
        if number_of_records[0] > 3000:
            return json.dumps('database too big (> 3000 records)')
        keys_list.sort()
        for item in keys_list:
            item_value = await self.get_value(item)
            item_name = codecs.escape_encode(item)[0].decode('ascii')  # type: ignore
            if mode == 'short':
                # Mode 'short' - exclude blockchain packages, blocks, and merkle nodes.
                if item_name.startswith(SHORT_MODE_EXCLUDE):
                    continue
            item_value_str = None if item_value is None else \
                codecs.escape_encode(item_value)[0].decode('ascii')  # type: ignore
            data[item_name] = item_value_str
        return json.dumps(data, indent=4, sort_keys=True)


class AerospikeLayeredStorage(AerospikeThreadedStorageBase):
    """
    Aerospike storage implementation using buckets of type map. Values written using this storage
    object are bucketed using {index_bits} bits of a hash on the key. Each bucket is an aerospike
    map object from the real key to the value.
    The reason we use this is to reduce the total amount of keys in aerospike, because they take
    RAM. When the values are small, this is inefficient. For maximum efficiency, the bucketing
    should give values of size ~ 10KB.
    """

    def __init__(self, hosts: List[Tuple[str, int]], namespace: str,
                 aero_set: str,
                 use_services_alternate: Optional[bool] = None,
                 max_workers: Optional[int] = None,
                 index_bits: Optional[int] = None):
        super().__init__(hosts, namespace, aero_set, use_services_alternate, max_workers)
        if index_bits is None:
            index_bits = 28
        self.index_bits = index_bits

    def get_bucket_key(self, key: bytes):
        # Returns the first self.index_bits bits of the hash of a key.
        x = int.from_bytes(hashlib.sha1(key).digest(), 'little')
        return (x & ((1 << self.index_bits) - 1)).to_bytes(8, 'little')

    def sync_get(self, key: bytes) -> Optional[bytes]:
        try:
            bucket_key = (self.namespace, self.aero_set, bytearray(self.get_bucket_key(key)))
            res = self.client.map_get_by_key(
                bucket_key, 'value', bytearray(key), aerospike.MAP_RETURN_KEY_VALUE)
            if len(res) == 0:
                return None
            # res must be of length 1 here.
            _, res_value = res[0]
            return bytes(res_value)
        except aerospike.exception.RecordNotFound:
            return None

    def sync_set(self, key: bytes, value: bytes, policy: dict):
        try:
            bucket_key = (self.namespace, self.aero_set, bytearray(self.get_bucket_key(key)))
            self.client.map_put(
                bucket_key, 'value', bytearray(key), bytearray(value),
                policy=policy)
            return True
        except aerospike.exception.RecordExistsError:
            return False

    def sync_del(self, key: bytes) -> bool:
        try:
            bucket_key = (self.namespace, self.aero_set, bytearray(self.get_bucket_key(key)))
            res = self.client.map_remove_by_key(bucket_key, 'value', bytearray(
                key), aerospike.MAP_RETURN_KEY_VALUE)
            return len(res) > 0
        except aerospike.exception.RecordNotFound:
            return False
