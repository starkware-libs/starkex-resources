from collections import defaultdict
from dataclasses import dataclass, field
from typing import Awaitable, Callable, ClassVar, Dict, Type

import marshmallow
import marshmallow_dataclass

from starkware.error_handling import (
    StarkMsg, stark_assert, stark_assert_eq, stark_assert_le, stark_assert_ne)
from starkware.storage import HASH_BYTES, Fact

from .fields import IntAsHex, IntAsStr

MAX_AMOUNT = 2 ** 63


@dataclass
class VaultUpdateData:
    vault_id: int
    stark_key: int = field(metadata={'marshmallow_field': IntAsHex(required=True)})
    token: int = field(metadata={'marshmallow_field': IntAsHex(required=True)})
    diff: int


@dataclass
class VaultState:
    stark_key: int = field(metadata={'marshmallow_field': IntAsHex(required=True)})
    token: int = field(metadata={'marshmallow_field': IntAsHex(required=True)})
    balance: int = field(metadata={'marshmallow_field': IntAsStr(required=True)})

    def __post_init__(self):
        stark_assert(
            0 <= self.balance < MAX_AMOUNT,
            StarkMsg.OUT_OF_RANGE_BALANCE,
            'Balance is negative or out of range')
        if self.balance == 0:
            self.stark_key = 0
            self.token = 0
        else:
            stark_assert_ne(0, self.stark_key, StarkMsg.INVALID_VAULT,
                            'A non empty vault cannot have an empty stark key')
            stark_assert_ne(0, self.token, StarkMsg.INVALID_VAULT,
                            'A non empty vault cannot have an empty token')

    @classmethod
    def empty(cls) -> 'VaultState':
        return cls(
            stark_key=0,
            token=0,
            balance=0,
        )

    def add(self, change: VaultUpdateData) -> 'VaultState':
        if self.balance > 0:
            # Vault is non-empty - validate it.
            stark_assert_eq(self.stark_key, change.stark_key, StarkMsg.INVALID_VAULT,
                            'Vault does not match stark_key')
            stark_assert_eq(self.token, change.token, StarkMsg.INVALID_VAULT,
                            'Vault does not match token')
        return self.__class__(stark_key=change.stark_key,
                              token=change.token,
                              balance=self.balance + change.diff)


@marshmallow_dataclass.dataclass
class VaultStateFact(VaultState, Fact):
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema

    @classmethod
    def prefix(cls):
        return b'vault_state'

    def serialize(self) -> bytes:
        return VaultStateFact.Schema().dumps(self).encode('ascii')  # type: ignore

    async def _hash(self, hash_func: Callable[[bytes, bytes], Awaitable[bytes]]) -> bytes:
        hash0 = await hash_func(self.stark_key.to_bytes(HASH_BYTES, 'big'),
                                self.token.to_bytes(HASH_BYTES, 'big'))
        return await hash_func(hash0, self.balance.to_bytes(HASH_BYTES, 'big'))

    @classmethod
    def deserialize(cls, data: bytes) -> 'VaultStateFact':
        return cls.Schema().loads(data)  # type: ignore


@dataclass
class OrderUpdateData:
    order_id: int
    diff: int
    capacity: int


@dataclass
class OrderState:
    fulfilled_amount: int = field(metadata={'marshmallow_field': IntAsStr(required=True)})

    def __post_init__(self):
        stark_assert(
            0 <= self.fulfilled_amount < MAX_AMOUNT,
            StarkMsg.INVALID_FULFILLED_AMOUNT,
            'Fulfilled amount is negative or out of range')

    @classmethod
    def empty(cls) -> 'OrderState':
        return cls(0)

    def add(self, change: OrderUpdateData) -> 'OrderState':
        stark_assert(
            0 <= change.diff < MAX_AMOUNT,
            StarkMsg.OUT_OF_RANGE_DIFF,
            f'Negative or out of range party sold value')
        stark_assert_le(
            self.fulfilled_amount + change.diff, change.capacity,
            StarkMsg.CONFLICTING_SETTLEMENT_AMOUNTS,
            f'Settlement fulfilled amounts exceeds capacity')
        return self.__class__(self.fulfilled_amount + change.diff)


@marshmallow_dataclass.dataclass
class OrderStateFact(OrderState, Fact):
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema

    @classmethod
    def prefix(cls):
        return b'order_state'

    def serialize(self) -> bytes:
        return OrderStateFact.Schema().dumps(self).encode('ascii')  # type: ignore

    async def _hash(self, hash_func: Callable[[bytes, bytes], Awaitable[bytes]]) -> bytes:
        return self.fulfilled_amount.to_bytes(HASH_BYTES, 'big')

    @classmethod
    def deserialize(cls, data: bytes) -> 'OrderStateFact':
        return cls.Schema().loads(data)  # type: ignore


@dataclass
class PartialState:
    vaults: Dict[int, VaultState]
    orders: Dict[int, OrderState]

    @classmethod
    def empty(cls):
        """
        A Full state, with all leaves filled with the empty leaf.
        This is different than a partial state, with missing keys.
        """
        return cls(
            vaults=defaultdict(VaultStateFact.empty),
            orders=defaultdict(OrderStateFact.empty),
        )

    def update_partial_state(self, vaults: Dict[int, VaultState],
                             orders: Dict[int, OrderState]) -> 'PartialState':
        new_vaults = vaults.copy()
        new_vaults.update(self.vaults)
        new_orders = orders.copy()
        new_orders.update(self.orders)
        return PartialState(vaults=new_vaults, orders=new_orders)

    def keep_diffs(self, reference_state):
        """
        Keeps only the leafs that were changed relative to 'reference_state'.

        self is modified in-place and all the unchanged leafs are deleted.
        """
        for vault_id, orig_state in reference_state.vaults.items():
            if self.vaults[vault_id] == orig_state:
                del self.vaults[vault_id]
        for order_id, orig_state in reference_state.orders.items():
            if self.orders[order_id] == orig_state:
                del self.orders[order_id]
        return self

    def __le__(self, other) -> bool:
        """
        Returns true if and only if this state is partial to other.
        """
        assert isinstance(other, PartialState)
        try:
            for k in self.vaults.keys():
                if self.vaults[k] != other.vaults[k]:
                    return False
            for k in self.orders.keys():
                if self.orders[k] != other.orders[k]:
                    return False
        except KeyError:
            return False
        return True

    def __eq__(self, other):
        return self <= other and other <= self
