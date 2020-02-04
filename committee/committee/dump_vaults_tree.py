import argparse
import asyncio
import csv
import sys
from typing import TextIO

import yaml

from starkware.crypto.signature.fast_pedersen_hash import async_pedersen_hash_func
from starkware.objects.state import VaultStateFact
from starkware.storage.merkle_tree import MerkleTree
from starkware.storage.storage import Storage


def parse_args():
    """
    Sets possible flags of arguments and parse the arguments accordingly
    Returns a dictionary with the parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="""\
Dumps a vaults tree from the database.

The output is composed of two csv files.
A nodes file and a vaults file.
The structure of the nodes file is:
"index node_hash"
where index is the index of the node in a "binary tree in array represention",
i.e. 2**(node_layer) + node_index_in_layer.

The structure of the vaults file is:
"vault_id stark_key token_id balance"
""")
    parser.add_argument('--root', type=str, default=None,
                        help='Root of vaults Merkle tree')
    parser.add_argument('--height', type=int, default=31, help='Height of vaults Merkle Tree')
    parser.add_argument('--nodes_file', type=str,
                        help='Name of the output nodes csv file', required=True)
    parser.add_argument('--vaults_file', type=str,
                        help='Name of the output vaults csv file', required=True)
    parser.add_argument('--config_file', type=str, default=None,
                        help='path to config file with storage configuration')

    args = parser.parse_args()

    return args


async def dump_vaults_tree(tree: MerkleTree, nodes_file: TextIO, vaults_file: TextIO):
    """
    Dump 'tree' into the given output files.
    """
    empty_trees = await MerkleTree.empty_tree_roots(
        tree.height, VaultStateFact(0, 0, 0), tree.hash_func)

    nodes_writer = csv.writer(nodes_file, delimiter=',')
    vaults_writer = csv.writer(vaults_file, delimiter=',')

    # Traverse the tree in DFS manner,
    # obtaining data from leaves, and ignoring empty subtrees.
    async for index, node in tree.dfs(exclude_set=set(empty_trees)):
        data = node.root.hex()
        nodes_writer.writerow([index, data])

        if node.height == 0 and node.root != empty_trees[0]:
            data = await VaultStateFact.get(tree.storage, node.root)
            vault_id = index - 2 ** tree.height
            vaults_writer.writerow(
                [vault_id, data.stark_key, data.token, data.balance])


async def main():
    args = parse_args()

    if args.config_file:
        config = yaml.safe_load(open(args.config_file))
    else:
        # default configuration assuming port forwarding.
        config = yaml.safe_load("""\
STORAGE:
    class: starkware.storage.aerospike_storage_threadpool.AerospikeLayeredStorage
    config:
        hosts:
        - localhost:3000
        namespace: starkware
        aero_set: starkware
        index_bits: 28
    """)

    storage = await Storage.from_config(config['STORAGE'])

    root_as_int = int(args.root, 16)
    tree = MerkleTree(root_as_int.to_bytes(32, 'big'), args.height,
                      storage, async_pedersen_hash_func)

    with open(args.nodes_file, 'w') as nodes_file, open(args.vaults_file, 'w') as vaults_file:
        await dump_vaults_tree(tree, nodes_file, vaults_file)


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
