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

import json
import logging
import os
import random

import pytest

from .signature import (
    FIELD_PRIME, InvalidPublicKeyError, get_limit_order_msg, get_random_private_key,
    get_transfer_msg, get_y_coordinate, pedersen_hash, private_key_to_ec_point_on_stark_curve,
    private_to_stark_key, sign, verify)

logger = logging.getLogger(__name__)


def test_get_y_coordinate():
    priv_key = get_random_private_key()
    public_key = private_key_to_ec_point_on_stark_curve(priv_key)
    y = get_y_coordinate(public_key[0])
    assert public_key[1] in [y, (-y) % FIELD_PRIME]
    with pytest.raises(InvalidPublicKeyError):
        get_y_coordinate(0)


def test_ecdsa_signature():
    priv_key = get_random_private_key()
    public_key = private_key_to_ec_point_on_stark_curve(priv_key)
    msg = random.randint(0, 2**251 - 1)
    r, w = sign(msg, priv_key)
    assert verify(msg, r, w, public_key)
    assert verify(msg, r, w, public_key[0])
    assert not verify(msg + 1, r, w, public_key)
    assert not verify(msg + 1, r, w, public_key[0])
    assert not verify(msg, r + 1, w, public_key)
    assert not verify(msg, r + 1, w, public_key[0])
    assert not verify(msg, r, w + 1, public_key)
    assert not verify(msg, r, w + 1, public_key[0])


@pytest.fixture
def data_file():
    json_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'signature_test_data.json')
    return json.load(open(json_file))


@pytest.mark.parametrize('pedersen_hash_data', ['pedersen_hash_data_1', 'pedersen_hash_data_2'])
def test_pedersen_hash(data_file, pedersen_hash_data):
    """
    Tests pedersen hash. Parameters are from signature_test_data.json.
    """
    assert pedersen_hash(
        int(data_file['hash_test'][pedersen_hash_data]['input_1'], 16),
        int(data_file['hash_test'][pedersen_hash_data]['input_2'], 16)) == \
        int(data_file['hash_test'][pedersen_hash_data]['output'], 16)


def test_order_message(data_file):
    """
    Tests order message. Parameters are from signature_test_data.json.
    """
    order = data_file['settlement']['party_a_order']
    limit_order_msg = get_limit_order_msg(
        vault_sell=int(order['vault_id_sell']), vault_buy=int(order['vault_id_buy']),
        amount_sell=int(order['amount_sell']), amount_buy=int(order['amount_buy']),
        token_sell=int(order['token_sell'], 16), token_buy=int(order['token_buy'], 16),
        nonce=order['nonce'],
        expiration_timestamp=order['expiration_timestamp'])
    assert limit_order_msg == int(data_file['meta_data']['party_a_order']['message_hash'], 16)


def test_transfer_message(data_file):
    """
    Tests transfer message. Parameters are from signature_test_data.json.
    """
    transfer = data_file['transfer_order']
    transfer_msg = get_transfer_msg(
        amount=int(transfer['amount']), nonce=1,
        sender_vault_id=int(transfer['sender_vault_id']),
        token=int(transfer['token'], 16),
        receiver_vault_id=int(transfer['target_vault_id']),
        receiver_public_key=int(transfer['target_public_key'], 16),
        expiration_timestamp=transfer['expiration_timestamp'])
    assert transfer_msg == int(data_file['meta_data']['transfer_order']['message_hash'], 16)


@pytest.mark.parametrize('order_data', ['party_a_order', 'party_b_order'])
def test_limit_order_signing_example(data_file, order_data):
    """
    Tests signing limit order. Parameters are from signature_test_data.json.
    """
    order = data_file['settlement'][order_data]
    private_key = int(data_file['meta_data'][order_data]['private_key'], 16)
    public_key = private_to_stark_key(private_key)
    msg = get_limit_order_msg(
        vault_sell=int(order['vault_id_sell']), vault_buy=int(order['vault_id_buy']),
        amount_sell=int(order['amount_sell']), amount_buy=int(order['amount_buy']),
        token_sell=int(order['token_sell'], 16), token_buy=int(order['token_buy'], 16),
        nonce=int(order['nonce']),
        expiration_timestamp=order['expiration_timestamp'])
    r, w = sign(msg, private_key)
    assert verify(msg, r, w, public_key)

    r = int(order['signature']['r'], 16)
    w = int(order['signature']['w'], 16)
    assert verify(msg, r, w, public_key)


def test_transfer_signing_example(data_file):
    """
    Tests signing transfer. Parameters are from signature_test_data.json.
    """
    private_key = int(data_file['meta_data']['party_a_order']['private_key'], 16)
    public_key = private_to_stark_key(private_key)
    transfer = data_file['transfer_order']
    transfer_msg = get_transfer_msg(
        amount=int(transfer['amount']), nonce=int(transfer['nonce']),
        sender_vault_id=int(transfer['sender_vault_id']),
        token=int(transfer['token'], 16),
        receiver_vault_id=int(transfer['target_vault_id']),
        receiver_public_key=int(transfer['target_public_key'], 16),
        expiration_timestamp=transfer['expiration_timestamp'])
    r, w = sign(transfer_msg, private_key)
    assert verify(transfer_msg, r, w, public_key)
    logger.info(f'transfer_msg signature: r: {r:x} w: {w:x}')
