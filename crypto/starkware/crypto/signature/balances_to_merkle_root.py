###############################################################################
# Copyright 2019 StarkWare Industries Ltd.                                    #
#                                                                             #
# Licensed under the Apache License, Version 2.0 (the "License").             #
# You may not use this file except in compliance with the License.            #
# You may obtain a copy of the License at                                     #
#                                                                             #
# https://www.starkware.co/open-source-license/                               #
#                                                                             #
# Unless required by applicable law or agreed to in writing,                  #
# software distributed under the License is distributed on an "AS IS" BASIS,  #
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.    #
# See the License for the specific language governing permissions             #
# and limitations under the License.                                          #
###############################################################################

import argparse
import asyncio
import concurrent
import contextlib
import json
import sys

from .signature import pedersen_hash


def vault_hash(stark_key, token_id, balance):
    """
    Each leaf in the Merkle tree represents a vault.
    Its value is derived from the stark_key, token_id pair it represents and the balance
    currently stored in the vault.
    """
    return pedersen_hash(pedersen_hash(stark_key, token_id), balance)


async def vault_hash_async(stark_key, token_id, balance, hash_func):
    """
    Similar to vault_hash, gets the hash func as parameter. Async.
    """
    return await hash_func(await hash_func(stark_key, token_id), balance)


def calc_zero_nodes(height):
    """
    Calculates the roots' hashes of trees with all zero leaves.
    Used to improve the running time of 'calc_root'.
    """
    zero_nodes_lookup = [vault_hash(0, 0, 0)]
    for i in range(height):
        zero_nodes_lookup.append(pedersen_hash(zero_nodes_lookup[-1], zero_nodes_lookup[-1]))
    return zero_nodes_lookup


async def calc_nodes(height, balances, zero_nodes_lookup, root_index, hash_func):
    """
    Returns all the nodes on the paths to the leaf balances 'balances' in the merkle tree
    of height 'height' with leaf balances 'balances'.
    'zero_nodes_lookup' is expected to contain roots' hashes of subtrees with all zero leaves.
    """
    if len(balances) == 0:
        return {root_index: zero_nodes_lookup[height]}
    if height == 0:
        assert len(balances) == 1
        _, vault_data = balances[-1]
        balance = int(vault_data['amount'])
        # A node with balance=0 is considered uninitialized.
        if balance == 0:
            return {root_index: zero_nodes_lookup[0]}
        stark_key = int(vault_data['stark_key'])
        token_id = int(vault_data['token_id'])
        return {root_index: await vault_hash_async(stark_key, token_id, balance, hash_func)}
    mid = 2 ** (height - 1)
    left_balances = [(i, data) for i, data in balances if i < mid]
    right_balances = [(i - mid, data) for i, data in balances if i >= mid]
    left, right = await asyncio.gather(
        calc_nodes(height - 1, left_balances, zero_nodes_lookup, 2 * root_index, hash_func),
        calc_nodes(height - 1, right_balances, zero_nodes_lookup, 2 * root_index + 1, hash_func))
    nodes = {root_index: await hash_func(left[2 * root_index], right[2 * root_index + 1])}
    nodes.update(left)
    nodes.update(right)
    return nodes


async def calc_root(height, balances, zero_nodes_lookup, hash_func):
    """
    Similar to calc_nodes, but computes only the root. Async.
    """
    if len(balances) == 0:
        return zero_nodes_lookup[height]
    if height == 0:
        assert len(balances) == 1
        _, vault_data = balances[-1]
        balance = int(vault_data['amount'])
        # A node with balance=0 is considered uninitialized.
        if balance == 0:
            return zero_nodes_lookup[0]
        stark_key = int(vault_data['stark_key'])
        token_id = int(vault_data['token_id'])
        return await vault_hash_async(stark_key, token_id, balance, hash_func)
    mid = 2 ** (height - 1)
    left_balances = [(i, data) for i, data in balances if i < mid]
    right_balances = [(i - mid, data) for i, data in balances if i >= mid]
    left, right = await asyncio.gather(
        calc_root(height - 1, left_balances, zero_nodes_lookup, hash_func),
        calc_root(height - 1, right_balances, zero_nodes_lookup, hash_func))
    return await hash_func(left, right)


def balances_to_path_nodes(balances_data, workers=1, hash_func=pedersen_hash):
    """
    Gets a dictionary that contains tree height and vaults data, and returns the node
    updates required to build the corresponding merkle tree.

    Note: if some vaults balance is zero, it will be treated as non-existent
    (with vault_hash(0, 0, 0)).

    example for 'balances_json':
    {
        "tree_height": 3,
        "vaults_data": [
            {
                "vault_id": 1
                "amount": 250,
                "stark_key":
                    524477289591696350496293706684471072993747699806458015336500686942778226900,
                "token_id":
                    119453999496103789726086117383575484401644694049581473658241312901726584202
            }
        ]
    }
    """
    height = balances_data['tree_height']
    vaults_data = balances_data['vaults_data']
    balances = [(vault['vault_id'], vault) for vault in vaults_data]

    event_loop = asyncio.new_event_loop()

    with parallel_hash(hash_func, workers) as async_hash_func:
        try:
            res = event_loop.run_until_complete(
                calc_nodes(height, balances, calc_zero_nodes(height), 1, async_hash_func)
            )
            return res
        finally:
            event_loop.close()


started = 0
finished = 0


@contextlib.contextmanager
def parallel_hash(hash_func, workers):
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        async def async_hash_func(x, y):
            global started, finished
            started += 1
            res = await asyncio.get_event_loop().run_in_executor(pool, hash_func, x, y)
            finished += 1

            if finished % 1000 == 0:
                print(started, finished)
            return res
        yield async_hash_func


def balances_to_merkle_root(balances_data, workers=1, hash_func=pedersen_hash):
    height = balances_data['tree_height']
    vaults_data = balances_data['vaults_data']
    balances = [(vault['vault_id'], vault) for vault in vaults_data]

    event_loop = asyncio.new_event_loop()

    with parallel_hash(hash_func, workers) as async_hash_func:
        try:
            res = event_loop.run_until_complete(
                calc_root(height, balances, calc_zero_nodes(height), async_hash_func)
            )
            return res
        finally:
            event_loop.close()


def parse_args():
    """
    Sets possible flags of arguments and parse the arguments accordingly.
    Returns a dictionary with the parsed arguments.
    """
    parser = argparse.ArgumentParser(description="""balances_to_merkle_root script.

    Expects a JSON file that contains tree height and vaults data, and prints the root of the
    corresponding merkle tree.
    """)
    parser.add_argument('--balances_file', required=True,
                        help='Json file containing the vaults balances.')
    parser.add_argument('--workers', type=int, default=8)

    args = parser.parse_args()
    return args


if __name__ == '__main__':
    args = parse_args()
    with open(args.balances_file) as balances_json:
        balances_data = json.load(balances_json)
    sys.stdout.write(str(balances_to_merkle_root(balances_data, args.workers)) + '\n')
