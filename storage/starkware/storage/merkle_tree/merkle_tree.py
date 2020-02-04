import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, List, Set, Tuple, Type, TypeVar

from ..storage import HASH_BYTES, Fact, Storage

TMerkleNodeFact = TypeVar('TMerkleNodeFact', bound='MerkleNodeFact')
TLeafNodeFact = TypeVar('TLeafNodeFact', bound='Fact')


@dataclass
class MerkleNodeFact(Fact):
    left_node: bytes
    right_node: bytes

    def serialize(self) -> bytes:
        return self.left_node + self.right_node

    @classmethod
    def deserialize(cls: Type[TMerkleNodeFact], data: bytes) -> TMerkleNodeFact:
        assert len(data) == 2 * HASH_BYTES
        return cls(
            left_node=data[:HASH_BYTES],
            right_node=data[HASH_BYTES:],
        )

    async def _hash(self, hash_func: Callable[[bytes, bytes], Awaitable[bytes]]) -> bytes:
        return await hash_func(self.left_node, self.right_node)

    @classmethod
    def prefix(cls) -> bytes:
        return b'merkle_node'


class MerkleTree:
    """
    An immutable Merkle tree backed by an immutable fact storage.
    """

    def __init__(self, root: bytes, height: int, storage: Storage,
                 hash_func: Callable[[bytes, bytes], Awaitable[bytes]]):
        self.root = root
        self.height = height
        self.storage = storage
        self.hash_func = hash_func

    @classmethod
    async def empty_tree(cls, height: int, storage: Storage, leaf_fact: Fact,
                         hash_func: Callable[[bytes, bytes], Awaitable[bytes]]) -> 'MerkleTree':
        """
        Initializes an empty MerkleTree where all the leaves' roots are equal to 'empty_leaf'.
        """
        assert height >= 0
        root = cls(await leaf_fact.set_fact(storage, hash_func), 0, storage, hash_func)
        for _ in range(height):
            root = await cls.combine(root, root)
        return root

    @classmethod
    async def combine(cls, left: 'MerkleTree', right: 'MerkleTree') -> 'MerkleTree':
        """
        Gets two MerkleTrees left and right and builds a fact which value is left's and right's
        roots and key is their hash, then writes it to the storage and returns a new MerkleTree
        representing this new fact.
        """
        assert left.height == right.height
        storage = left.storage
        assert left.hash_func == right.hash_func
        hash_func = left.hash_func

        root_fact = MerkleNodeFact(left.root, right.root)
        root = await root_fact.set_fact(storage, hash_func)
        return cls(root, left.height + 1, storage, hash_func)

    @staticmethod
    async def empty_tree_roots(
            max_height: int, leaf_fact: Fact,
            hash_func: Callable[[bytes, bytes], Awaitable[bytes]]) -> List[bytes]:
        """
        Returns a list of roots of empty trees with height up to 'max_height'.
        """
        assert max_height >= 0
        roots = [await leaf_fact._hash(hash_func)]

        for _ in range(max_height):
            roots.append(await hash_func(roots[-1], roots[-1]))
        return roots

    async def dfs(self, exclude_set: Set[bytes]):
        """
        Iterates the tree in DFS order while skipping subtrees with roots in the exclude_set.
        Note that nodes in the exclude_set are returned but their subtree is not visited.

        empty_trees = MerkleTree.empty_tree_roots(tree.height, empty_leaf, hash_func)
        async for index, node in tree.dfs(set(empty_trees)):
            ...

        The returned nodes are indexed using "binary tree in array" indexing to help
        keep track of the location in the tree.
        """
        async def dfs_inner(tree, index):
            yield (index, tree)
            if tree.height == 0 or tree.root in exclude_set:
                return

            for offset, child in enumerate(await tree.get_children()):
                async for res in dfs_inner(child, (2 * index) + offset):
                    yield res

        async for res in dfs_inner(self, 1):
            yield res

    async def get_children(self) -> Tuple['MerkleTree', 'MerkleTree']:
        """
        Returns the two MerkleTrees which are the subtrees of the current MerkleTree.
        """
        root_fact = await MerkleNodeFact.get(self.storage, self.root)
        assert root_fact is not None, 'Missing node in db'
        return MerkleTree(root_fact.left_node, self.height - 1, self.storage, self.hash_func), \
            MerkleTree(root_fact.right_node, self.height - 1, self.storage, self.hash_func)

    async def get_leaves(self, indices: List[int], fact_cls: Type[TLeafNodeFact]) -> \
            Dict[int, TLeafNodeFact]:
        """
        Returns the values of the leaves which indices are given.
        """
        if len(indices) == 0:
            return {}
        if self.height == 0:
            leaf = await fact_cls.get(self.storage, self.root)
            assert leaf is not None, 'Missing leaf in db'
            return {0: leaf}
        left, right = await self.get_children()
        mid = 2 ** (self.height - 1)
        left_indices = [index for index in indices if index < mid]
        right_indices = [(index - mid) for index in indices if index >= mid]

        left_leaves, right_leaves = await asyncio.gather(
            left.get_leaves(left_indices, fact_cls),
            right.get_leaves(right_indices, fact_cls))
        return {**left_leaves, **{x + mid: y for x, y in right_leaves.items()}}

    async def get_authentication_path(self, index) -> List[bytes]:
        """
        Returns the siblings of the nodes on the path from the root to the 'index'th leaf.
        """
        if self.height == 0:
            return []
        left, right = await self.get_children()
        mid = 2 ** (self.height - 1)

        if index >= mid:
            return await right.get_authentication_path(index - mid) + [left.root]
        return await left.get_authentication_path(index) + [right.root]

    async def update(self, modifications: List[Tuple[int, Fact]]) -> 'MerkleTree':
        """
        Updates the tree with the given list of modifications, writes all the new facts to the
        storage and returns a new MerkleTree representing the fact of the root of the new tree.
        """
        if len(modifications) == 0:
            return self
        if self.height == 0:
            index, fact = modifications[-1]
            assert index == 0
            return MerkleTree(
                await fact.set_fact(self.storage, self.hash_func),
                0,
                self.storage,
                self.hash_func)
        left, right = await self.get_children()
        mid = 2 ** (self.height - 1)
        left_modifications = [(i, val) for i, val in modifications if i < mid]
        right_modifications = [(i - mid, val) for i, val in modifications if i >= mid]
        if len(left_modifications) == 0:
            right = await right.update(right_modifications)
        elif len(right_modifications) == 0:
            left = await left.update(left_modifications)
        else:
            left, right = await asyncio.gather(
                left.update(left_modifications),
                right.update(right_modifications))
        new_root = await MerkleTree.combine(left, right)
        return new_root


async def calc_root(index: int, value: bytes, path: List[bytes],
                    hash_func: Callable[[bytes, bytes], Awaitable[bytes]]):
    """
    Calculates the root of a merkle tree from a given value residing in leaf
    with a given index and an authentication path using hash_func.
    """
    if len(path) == 0:
        return value
    mid = 2 ** (len(path) - 1)

    if index >= mid:
        return await hash_func(
            path[-1], await calc_root(index - mid, value, path[:-1], hash_func))
    return await hash_func(
        await calc_root(index, value, path[:-1], hash_func), path[-1])


async def verify_path(root: bytes, index: int, value: bytes, path: List[bytes],
                      hash_func: Callable[[bytes, bytes], Awaitable[bytes]]) -> bool:
    """
    Verifies a Merkle proof implied by an authentication path, that a given value resides in leaf
    with a given index in a Merkle tree whose root is also given, and was constructed using
    hash_func.
    """

    return root == await calc_root(index, value, path, hash_func)
