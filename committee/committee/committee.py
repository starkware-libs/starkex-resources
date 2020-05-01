import asyncio
import concurrent
import logging
import logging.config
import os
import sys
from dataclasses import field
from typing import ClassVar, Type

import marshmallow
import yaml
from marshmallow_dataclass import dataclass
from web3 import eth

from starkware.availability_claim import hash_availability_claim
from starkware.crypto.signature.fast_pedersen_hash import pedersen_hash_func
from starkware.objects.availability import StateUpdate
from starkware.objects.fields import BytesAsHex
from starkware.objects.state import OrderStateFact, VaultStateFact
from starkware.storage.imm_storage import immediate_storage
from starkware.storage.merkle_tree import MerkleTree
from starkware.storage.storage import Storage

from .availability_gateway_client import AvailabilityGatewayClient
from .custom_validation import is_valid

logger = logging.getLogger(__package__)


@dataclass
class CommitteeBatchInfo():
    vaults_root: bytes = field(metadata={'marshmallow_field': BytesAsHex(required=True)})
    orders_root: bytes = field(metadata={'marshmallow_field': BytesAsHex(required=True)})
    sequence_number: int
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema

    def serialize(self) -> bytes:
        return CommitteeBatchInfo.Schema().dumps(self).encode('ascii')

    @classmethod
    def deserialize(cls, data: bytes) -> 'CommitteeBatchInfo':
        return cls.Schema().loads(data.decode('ascii'))


class Committee:
    def __init__(self, config: dict, private_key: str, storage: Storage,
                 merkle_storage: Storage, hash_func, availability_gateway):
        self.storage = storage
        self.merkle_storage = merkle_storage
        self.hash_func = hash_func
        self.vaults_merkle_height = config['VAULTS_MERKLE_HEIGHT']
        self.orders_merkle_height = config['ORDERS_MERKLE_HEIGHT']

        self.availability_gateway = availability_gateway
        self.account = eth.Account.from_key(private_key)
        self.polling_interval = config['POLLING_INTERVAL']
        self.validate_orders = bool(config.get('VALIDATE_ORDERS', False))
        if self.validate_orders:
            logger.info('Full validation mode enabled: validating both vaults and orders.')
        else:
            logger.info('Validating only vault data-availability.')
        self.stopped = False

    def stop(self):
        self.stopped = True

    @staticmethod
    def next_batch_id_key() -> bytes:
        return 'committee_next_batch_id'.encode('ascii')

    @staticmethod
    def committee_batch_info_key(batch_id: int) -> bytes:
        return f'committee_batch_info:{batch_id}'.encode('ascii')

    async def compute_initial_batch_info(self):
        # Compute a CommitteeBatchInfo with empty Merkle trees and sequence_number == -1.
        initial_batch_id = -1
        async with immediate_storage(self.merkle_storage) as storage:
            vaults_tree, orders_tree = await asyncio.gather(
                MerkleTree.empty_tree(
                    self.vaults_merkle_height, storage, VaultStateFact.empty(),
                    self.hash_func),
                MerkleTree.empty_tree(
                    self.orders_merkle_height, storage, OrderStateFact(0), self.hash_func),
            )

            initial_batch_info = CommitteeBatchInfo(
                vaults_tree.root, orders_tree.root, sequence_number=-1).serialize()
        await self.storage.set_value(
            self.committee_batch_info_key(initial_batch_id), initial_batch_info)

    async def validate_data_availability(self, batch_id: int,
                                         state_update: StateUpdate, validate_orders: bool):
        """
        Given the state_update for a new batch, verify data availability by computing
        the roots for the new batch.

        The new roots are stored in storage along with the sequence number
        and a signed availability_claim is sent to the availability gateway.
        """

        prev_batch_info = await self.storage.get_value(
            Committee.committee_batch_info_key(state_update.prev_batch_id))
        assert prev_batch_info is not None, \
            f'Prev batch not found for batch_id {state_update.prev_batch_id}'

        logger.info(f'Processing batch {batch_id}')
        logger.info(f'Using batch {state_update.prev_batch_id} as reference')

        prev_batch_info = CommitteeBatchInfo.deserialize(prev_batch_info)

        # Task to compute the new vault root.
        async def compute_vault_root(storage):
            vault_tree = MerkleTree(prev_batch_info.vaults_root, self.vaults_merkle_height,
                                    storage, self.hash_func)
            vault_tree = await vault_tree.update(state_update.vaults.items())
            return vault_tree.root.hex()

        # Task to compute the new order root.
        async def compute_order_root(storage):
            order_tree = MerkleTree(prev_batch_info.orders_root, self.orders_merkle_height,
                                    storage, self.hash_func)
            order_tree = await order_tree.update(state_update.orders.items())
            return order_tree.root.hex()

        # Verify consistency of data with roots.
        async with immediate_storage(self.merkle_storage) as storage:
            if validate_orders:
                vault_root, order_root = await asyncio.gather(
                    compute_vault_root(storage), compute_order_root(storage))
                assert vault_root == state_update.vault_root, 'vault root mismatch'
                assert order_root == state_update.order_root, 'order root mismatch'
                logger.info(f'Verified vault root: 0x{state_update.vault_root}')
                logger.info(f'Verified order root: 0x{state_update.order_root}')
            else:
                vault_root = await compute_vault_root(storage)
                assert vault_root == state_update.vault_root, 'vault root mismatch'
                logger.info(f'Verified vault root: 0x{state_update.vault_root}')
                logger.info(f'Blindly signing order root: 0x{state_update.order_root}')

            batch_info = CommitteeBatchInfo(  # type: ignore
                bytes.fromhex(state_update.vault_root), bytes.fromhex(state_update.order_root),
                prev_batch_info.sequence_number + 1)

        await self.storage.set_value(
            self.committee_batch_info_key(batch_id), batch_info.serialize())

        logger.info(f'Signing batch with sequence number {batch_info.sequence_number}')

        availability_claim = hash_availability_claim(
            batch_info.vaults_root, self.vaults_merkle_height, batch_info.orders_root,
            self.orders_merkle_height, batch_info.sequence_number)
        signature = eth.Account._sign_hash(availability_claim, self.account.key).signature.hex()
        return signature, availability_claim.hex()

    async def run(self):
        next_batch_id = await self.storage.get_int(Committee.next_batch_id_key())
        if next_batch_id is None:
            await self.compute_initial_batch_info()
            next_batch_id = 0
            await self.storage.set_int(Committee.next_batch_id_key(), next_batch_id)

        while not self.stopped:
            try:
                availability_update = await self.availability_gateway.get_batch_data(next_batch_id)
                if availability_update is None:
                    logger.info(f'Waiting for batch {next_batch_id}')
                    await asyncio.sleep(self.polling_interval)
                    continue
                assert await is_valid(availability_update, next_batch_id), 'Third party validation failed.'
                signature, availability_claim = await self.validate_data_availability(
                    next_batch_id, availability_update, self.validate_orders)
                await self.availability_gateway.send_signature(
                    next_batch_id, signature, self.account.address, availability_claim)
                next_batch_id += 1
                await self.storage.set_int(Committee.next_batch_id_key(), next_batch_id)
            except Exception:
                logger.error('Got an exception:', exc_info=True)
                await asyncio.sleep(self.polling_interval)


async def main():
    config = yaml.safe_load(open('/config.yml', 'r'))
    private_key_path = os.environ.get(
        'PRIVATE_KEY_PATH', config.get('PRIVATE_KEY_PATH', '/private_key.txt'))
    with open(private_key_path, 'r') as private_key_file:
        # Read private_key from file (remove '\n' from end of line).
        private_key = private_key_file.read().rstrip()
    logging.config.dictConfig(config.get('LOGGING', {}))
    storage = await Storage.from_config(config.get('STORAGE'), logger=logger)

    availability_gw_endpoint = os.environ.get(
        'AVAILABILITY_GW_ENDPOINT', config.get('AVAILABILITY_GW_ENDPOINT'))

    certificates_path = os.environ.get(
        'CERTIFICATES_PATH', config.get('CERTIFICATES_PATH'))

    requests_kwargs = {}
    if certificates_path is not None:
        requests_kwargs = {'cert': (os.path.join(certificates_path, 'user.crt'),
                                    os.path.join(certificates_path, 'user.key')),
                           'verify': os.path.join(certificates_path, 'server.crt')}

    availability_gateway = AvailabilityGatewayClient(
        availability_gw_endpoint, requests_kwargs=requests_kwargs)
    logger.info(f'Using {availability_gw_endpoint} as an availability gateway')

    workers = int(os.environ.get('HASH_WORKERS', os.cpu_count()))
    logger.info(f'Using {workers} hashing process')

    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        async def async_hash_func(x, y):
            return await asyncio.get_event_loop().run_in_executor(pool, pedersen_hash_func, x, y)
        committee = Committee(
            config=config,
            private_key=private_key,
            storage=storage,
            merkle_storage=storage,
            hash_func=async_hash_func, availability_gateway=availability_gateway)
        await committee.run()


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
