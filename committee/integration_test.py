import asyncio
import csv
import logging
import os
import subprocess
import tempfile
import time

import requests
import yaml

from committee.dump_vaults_tree import dump_vaults_tree
from starkware.crypto.signature.fast_pedersen_hash import async_pedersen_hash_func
from starkware.objects.state import VaultStateFact
from starkware.storage.merkle_tree import MerkleTree
from starkware.storage.storage import Storage

logger = logging.getLogger(__name__)


async def dump_vaults_tree_test(storage_config):
    """
    The test dumps a vault tree with a specific root.
    After dumping all the data it goes over the dump and collects the information
    that is associated with a specific vault_id.
    It checks that the vault information is consistent with the hash of the corresponding leaf,
    and that the authentication path generated from the dumped data is the same
    as the authentication path generated using MerkleTree.get_authentication_path().
    """

    root = 0x0109bbc8b615885cafd7a2120e2f3c3218abde7b01a0abe5f772ab32dfe55861
    height = 31
    vault_id = 2136494259

    storage = await Storage.from_config(storage_config, logger=logger)
    tree = MerkleTree(root.to_bytes(32, 'big'), height, storage, async_pedersen_hash_func)

    nodes_file = tempfile.TemporaryFile(mode='r+')
    vaults_file = tempfile.TemporaryFile(mode='r+')
    await dump_vaults_tree(tree, nodes_file, vaults_file)

    vault_hash = None

    nodes_file.seek(0)
    reader = csv.reader(nodes_file, delimiter=',')

    index = vault_id + 2 ** height
    # Compute the indices of all the nodes in the authentication path.
    authentication_path_indices = [(index >> (height - 1 - depth)) ^ 1 for depth in range(height)]
    path = {}

    # Go over the csv file and collect the following hashes:
    # 1. vault_hash corresponding to vault_id
    # 2. hashes of nodes in the authentication path for the vault in 1.
    for row in reader:
        row_number = int(row[0])
        if row_number == index:
            vault_hash = row[1]
        if row_number in authentication_path_indices:
            path[row_number] = row[1]

    assert sorted(path.keys()) == authentication_path_indices

    vault_data = None

    vaults_file.seek(0)
    reader = csv.reader(vaults_file, delimiter=',')
    for row in reader:
        row_number = int(row[0])
        if row_number == index - 2**31:
            vault_data = VaultStateFact(int(row[1]), int(row[2]), int(row[3]))

    computed_vault_hash = (await vault_data._hash(async_pedersen_hash_func)).hex()
    assert computed_vault_hash == vault_hash,  f'{computed_vault_hash} != {vault_hash}'

    sorted_path = [root for index, root in sorted(path.items(), reverse=True)]

    # in the tree indexes are zero based.
    # while here the vaults start at offset 2**args.height.
    expected_path = [root.hex()
                     for root in await tree.get_authentication_path(index - 2 ** tree.height)]

    assert sorted_path == expected_path


def test_committee():
    """
    Tests the committee against a mock implementation of the availability verifier.
    """
    flavor = 'Release'
    build_path = os.path.join(os.path.dirname(__file__), f'../build/{flavor}')
    workdir = os.path.join(build_path, 'committee')
    report_dir = os.path.join(build_path, f'../reports/{flavor}')
    timeout = 60
    try:
        if os.environ.get('USE_LOCAL_DOCKERS') != '1':
            subprocess.check_call(['docker-compose', 'down'], cwd=workdir)
            subprocess.check_call(['docker-compose', 'build'], cwd=workdir)
            subprocess.check_call(['docker-compose', 'up', '-d'], cwd=workdir)
        start_time = time.time()
        n_batches_validated = 0
        while n_batches_validated < 3:
            time.sleep(1)
            if time.time() - start_time > timeout:
                raise TimeoutError
            try:
                resp = requests.request(
                    'GET',
                    'http://localhost:9414/availability_gateway/get_num_validated_batches')
            except requests.exceptions.ConnectionError:
                logger.info('Failed to query gateway.', exc_info=True)
                continue

            if resp.status_code != 200:
                logger.info(f'got code {resp.status_code}:, {resp.text}')
                continue

            n_batches_validated = int(resp.text)

        # Test dump_db flow after the db is initialized and before we bring it down.
        config = yaml.safe_load(open(os.path.join(workdir, 'config.yml'), 'r'))
        config['STORAGE']['config']['hosts'] = ['localhost:3000']
        asyncio.run(dump_vaults_tree_test(config['STORAGE']))

    finally:
        os.makedirs(report_dir, exist_ok=True)
        log_file = tempfile.NamedTemporaryFile(
            prefix='log_',
            suffix='.txt',
            delete=False,
            dir=report_dir)
        print(f'Writing docker logs into {os.path.abspath(log_file.name)}')
        subprocess.call(['docker-compose', 'logs', '--no-color'],
                        cwd=workdir, stdout=log_file)

        subprocess.call(['docker-compose', 'logs', 'mock_availability_gateway'], cwd=workdir)
        if os.environ.get('USE_LOCAL_DOCKERS') != '1':
            subprocess.call(['docker-compose', 'down'], cwd=workdir)
