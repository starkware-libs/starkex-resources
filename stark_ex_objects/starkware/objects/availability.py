from typing import ClassVar, Dict, Optional, Type

import marshmallow
from marshmallow_dataclass import dataclass

from .state import OrderStateFact, VaultStateFact


@dataclass
class StateUpdate:
    """
    The information describing a state update.

    :param vaults: Dictionary mapping vault_id to vault state.
    :type vaults: dict
    :param orders: Dictionary mapping order_id to order state.
    :type orders: dict
    :param vault_root: expected vault root after update.
    :type vault_root: hex str (without any prefix)
    :param order_root: expected order root after update.
    :type order_root: hex str (without any prefix)
    :param prev_batch_id: Previous batch ID.
    :type prev_batch_id: int
    """
    vaults: Dict[int, VaultStateFact]
    orders: Dict[int, OrderStateFact]
    vault_root: str
    order_root: str
    prev_batch_id: int
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema


@dataclass
class BatchDataResponse:
    update: Optional[StateUpdate]
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema


@dataclass
class CommitteeSignature:
    """
    The information describing a committee signature.

    :param batch_id: ID of signed batch.
    :type batch_id: int
    :param signature: Committee signature for batch.
    :type signature: str
    :param member_key: Committee member public key used for identification.
    :type member_key: str
    :param claim_hash: Claim hash being signed used for validating the expected claim.
    :type claim_hash: str
    """
    batch_id: int
    signature: str
    member_key: str
    claim_hash: str
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema
