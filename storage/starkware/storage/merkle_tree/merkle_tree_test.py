import asyncio
import random
from dataclasses import dataclass
from typing import Awaitable, Callable, Type, TypeVar

import pytest

from ..imm_storage import immediate_storage
from ..storage import HASH_BYTES, Fact
from ..test_utils import DelayedStorage, MockStorage, hash_func, timed_call
from .merkle_tree import MerkleTree, verify_path

TDummyLeaf = TypeVar('TDummyLeaf', bound='DummyLeaf')
@dataclass
class DummyLeaf(Fact):
    value: int

    @classmethod
    def prefix(cls):
        return b'dummy'

    def serialize(self) -> bytes:
        return self.value.to_bytes(HASH_BYTES, 'big')

    async def _hash(self, hash_func: Callable[[bytes, bytes], Awaitable[bytes]]) -> bytes:
        return await hash_func(self.serialize(), b'\0'*HASH_BYTES)

    @classmethod
    def deserialize(cls: Type[TDummyLeaf], data: bytes) -> TDummyLeaf:
        return cls(int.from_bytes(data, 'big'))


def get_previous_root(batches, index):
    """
    Returns the root on which we want to apply the batch.
    In case it is the first batch, None is returned.
    """
    previous_batch_index = batches[index]['previous_batch_index']
    if previous_batch_index is None:
        return None
    return batches[previous_batch_index]['root_after']


def get_expected_leaves_dict(height, batches, index):
    """
    Returns the expected dict of leaves according to the batches order determined by
    'previous_batch_index'.
    """
    n_leaves = 2 ** height
    leaves = {i: DummyLeaf(0) for i in range(n_leaves)}
    batches_indices_list = [index]
    previous_batch_index = batches[index]['previous_batch_index']
    while previous_batch_index is not None:
        batches_indices_list.append(previous_batch_index)
        previous_batch_index = batches[previous_batch_index]['previous_batch_index']
    for i in reversed(batches_indices_list):
        curr_batch = batches[i]
        modifications = curr_batch['modifications']
        for j in range(len(modifications)):
            index, new_value = modifications[j]
            leaves[index] = new_value
    return leaves


async def merkle_tree_test(height, modifications):
    """
    Constructs an empty_tree, checks all leaves are empty, then updates it with a list
    of modifications and checks that the leaves have changed.
    """
    n_leaves = 2 ** height

    storage = MockStorage()

    # Construct an empty tree of hight = 5.
    empty_tree = await MerkleTree.empty_tree(height, storage, DummyLeaf(0), hash_func)
    # Set expected_leaves_dict to be a dict of empty leaves.
    expected_leaves_dict = {i: DummyLeaf(0) for i in range(n_leaves)}
    # Get a dict with all leaves values from the constructed tree.
    leaves_dict = await empty_tree.get_leaves(range(n_leaves), DummyLeaf)

    assert leaves_dict == expected_leaves_dict

    # Update empty_tree with the list of modifications, obtaining a new tree.
    new_root = await empty_tree.update(modifications)
    # Update expected_leaves_dict with the dict of modifications.
    for i in range(len(modifications)):
        expected_leaves_dict[modifications[i][0]] = modifications[i][1]
    # Get a dict with all leaves values from the new tree.
    leaves_dict = await new_root.get_leaves(range(n_leaves), DummyLeaf)

    assert leaves_dict == expected_leaves_dict


@pytest.mark.asyncio
async def test_merkle_empty_tree_roots():
    height = 5

    empty_leaf = DummyLeaf(0)
    empty_trees = await MerkleTree.empty_tree_roots(height, empty_leaf, hash_func)
    assert len(empty_trees) == height + 1, f'excpecting roots for heights: 0, 1, ..., {height}'

    empty_leaf_hash = await empty_leaf._hash(hash_func)
    assert empty_trees[0] == empty_leaf_hash
    assert empty_trees[1] == await hash_func(empty_leaf_hash, empty_leaf_hash)

    storage = MockStorage()
    exected_last_root = (await MerkleTree.empty_tree(height, storage, empty_leaf, hash_func)).root
    assert empty_trees[-1] == exected_last_root


@pytest.mark.asyncio
async def test_dfs():
    height = 2
    storage = MockStorage()
    empty_leaf = DummyLeaf(0)
    empty_tree = await MerkleTree.empty_tree(height, storage, empty_leaf, hash_func)

    modifications = [[3, DummyLeaf(4)]]
    # Update empty_tree with the list of modifications, obtaining a new tree.
    tree = await empty_tree.update(modifications)

    empty_trees = await MerkleTree.empty_tree_roots(tree.height, empty_leaf, hash_func)
    visited = []
    async for index, node in tree.dfs(set(empty_trees)):
        visited.append((index, node.root))

    empty_leaf_hash = await empty_leaf._hash(hash_func)
    non_empty_leaf_hash = await DummyLeaf(4)._hash(hash_func)
    expected_roots = [(1, tree.root), (2, empty_trees[1]),
                      (3, await hash_func(empty_leaf_hash, non_empty_leaf_hash)),
                      (6, empty_leaf_hash), (7, non_empty_leaf_hash)]

    assert visited == expected_roots


@pytest.mark.asyncio
async def test_merkle_tree():
    """
    A basic Merkle test, applying 3 hard-coded modifications and checking that the resulting tree
    is correct.
    """
    height = 5
    modifications = [[25, DummyLeaf(2)], [8, DummyLeaf(4)], [9, DummyLeaf(1)]]
    await merkle_tree_test(height, modifications)


@pytest.mark.asyncio
async def test_random_modifications():
    """
    A basic Merkle test, applying 10 random modifications and checking that the resulting tree
    is correct.
    """
    height = 5
    n_leaves = 2 ** height
    n_modifications = 10
    random.seed()
    modifications = [[random.randint(0, n_leaves - 1), DummyLeaf(random.randint(0, 9))]
                     for i in range(n_modifications)]
    await merkle_tree_test(height, modifications)


@pytest.mark.asyncio
async def test_verify_path():
    """
    Constructs an empty_tree and updates it with a list of modifications, then gets an
    authentication path of one of the modified roots and check that it is verified correctly.
    Also tweaks the value, index and tree to obtain incorrect proofs and make sure they are
    rejected.
    """
    height = 5

    storage = MockStorage()

    # Construct an empty tree of hight = 5.
    empty_tree = await MerkleTree.empty_tree(height, storage, DummyLeaf(0), hash_func)

    modifications = [[25, DummyLeaf(2)], [8, DummyLeaf(4)], [9, DummyLeaf(1)]]
    # Update empty_tree with the list of modifications, obtaining a new tree.
    new_root = await empty_tree.update(modifications)

    index = modifications[0][0]
    value = modifications[0][1]
    # Get the authentication path of the leaf at index 'index' on the tree after the update.
    path = await new_root.get_authentication_path(index)

    # Verify the authentication path on the new tree (with correct index and value).
    assert await verify_path(new_root.root, index, await value._hash(hash_func), path, hash_func)

    # verify_path should fail when the value is incorrect.
    assert not await verify_path(new_root.root, index, await DummyLeaf(3)._hash(hash_func), path,
                                 hash_func)

    # verify_path should fail when the index is incorrect.
    assert not await verify_path(
        new_root.root, index + 1, await value._hash(hash_func), path, hash_func)

    # verify_path should fail with new path in old tree.
    assert not await verify_path(
        empty_tree.root, index, await value._hash(hash_func), path, hash_func)


@pytest.mark.asyncio
async def test_batches_and_revert():
    """
    Tests MerkleTree by making a sequence of three batches on an initial tree (all-zero leaves)
    then discards the last two and makes another (following to the first batch).
    """
    height = 5

    batches = [{'previous_batch_index': None,
                'modifications': [[25, DummyLeaf(2)], [8, DummyLeaf(4)], [9, DummyLeaf(1)]]},
               {'previous_batch_index': 0,
                'modifications': [[8, DummyLeaf(9)], [15, DummyLeaf(7)], [23, DummyLeaf(5)]]},
               {'previous_batch_index': 1,
                'modifications': [[4, DummyLeaf(6)], [16, DummyLeaf(4)], [6, DummyLeaf(8)]]},
               {'previous_batch_index': 0,
                'modifications': [[20, DummyLeaf(3)], [11, DummyLeaf(1)], [5, DummyLeaf(8)]]}]

    n_batches = len(batches)

    storage = MockStorage()
    current_tree = await MerkleTree.empty_tree(height, storage, DummyLeaf(0), hash_func)

    for i in range(n_batches):
        previous_root = get_previous_root(batches, i)
        if previous_root is None:
            previous_root = current_tree
        new_root = await previous_root.update(batches[i]['modifications'])
        batches[i]['root_after'] = new_root
        expected_leaves_dict = get_expected_leaves_dict(height, batches, i)
        leaves_dict = await batches[i]['root_after'].get_leaves(range(2 ** height), DummyLeaf)
        assert leaves_dict == expected_leaves_dict


def get_delayed_hash(delay):
    """
    Returns a delayed version for testing hash_func.
    """
    async def delayed_hash(left, right):
        await asyncio.sleep(delay)
        return await hash_func(left, right)
    return delayed_hash


@pytest.mark.asyncio
@pytest.mark.parametrize('read_delay', [0.002, 0.01])
@pytest.mark.parametrize('write_delay', [0.002, 0.01])
@pytest.mark.parametrize('hash_delay', [0.002, 0.01])
async def test_async_times(read_delay, write_delay, hash_delay):
    """
    Tests async Merkle while introducing artificial delays to simulate a real system. We then check
    that the asynchronous calls indeed take the expected time.
    """
    height = 5
    storage = DelayedStorage(read_delay, write_delay)
    hash_f = get_delayed_hash(hash_delay)

    with timed_call((height + 1) * (write_delay + hash_delay)):
        tree = await MerkleTree.empty_tree(height, storage, DummyLeaf(0), hash_f)

    modifications = [(i, DummyLeaf(1)) for i in range(2 ** height)]
    with timed_call((height + 1) * (hash_delay + write_delay) + height * read_delay):
        await tree.update(modifications)

    with timed_call((height + 1) * read_delay):
        await tree.get_leaves(range(2 ** height), DummyLeaf)


@pytest.mark.asyncio
@pytest.mark.parametrize('read_delay', [0.02, 0.1])
@pytest.mark.parametrize('write_delay', [0.02, 0.1])
@pytest.mark.parametrize('hash_delay', [0.02, 0.1])
async def test_async_times_imm(read_delay, write_delay, hash_delay):
    """
    Tests async Merkle while introducing artificial delays to simulate a real system. We then check
    that the asynchronous calls indeed take the expected time.
    """
    height = 5
    hash_f = get_delayed_hash(hash_delay)
    back_storage = DelayedStorage(read_delay, write_delay)

    with timed_call((height + 1) * hash_delay * 2 + write_delay):
        async with immediate_storage(back_storage) as storage:
            with timed_call((height + 1) * hash_delay):
                tree = await MerkleTree.empty_tree(height, storage, DummyLeaf(0), hash_f)

            modifications = [(i, DummyLeaf(1)) for i in range(2 ** height)]
            with timed_call((height + 1) * hash_delay):
                await tree.update(modifications)

            with timed_call(0):
                await tree.get_leaves(range(2 ** height), DummyLeaf)
