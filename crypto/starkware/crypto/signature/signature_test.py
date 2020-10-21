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
from typing import Dict

import pytest

from .signature import (
    EC_ORDER, FIELD_PRIME, N_ELEMENT_BITS_ECDSA, InvalidPublicKeyError, get_random_private_key,
    get_y_coordinate, pedersen_hash, private_key_to_ec_point_on_stark_curve, private_to_stark_key,
    sign, verify)
from .starkex_messages import get_limit_order_msg, get_transfer_msg

logger = logging.getLogger(__name__)


def test_get_y_coordinate():
    priv_key = get_random_private_key()
    public_key = private_key_to_ec_point_on_stark_curve(priv_key)
    y = get_y_coordinate(public_key[0])
    assert public_key[1] in [y, (-y) % FIELD_PRIME]
    with pytest.raises(InvalidPublicKeyError):
        get_y_coordinate(0)


def test_verify_size_failure():
    max_msg = 2 ** N_ELEMENT_BITS_ECDSA - 1
    max_r = 2 ** N_ELEMENT_BITS_ECDSA - 1
    max_s = EC_ORDER - 2
    stark_key = private_to_stark_key(get_random_private_key())
    # Test invalid message length.
    with pytest.raises(AssertionError, match='msg_hash = %s' % str(max_msg + 1)):
        verify(max_msg + 1, max_r, max_s, stark_key)
    # Test invalid r length.
    with pytest.raises(AssertionError, match='r = %s' % str(max_r + 1)):
        verify(max_msg, max_r + 1, max_s, stark_key)
    # Test invalid w length.
    with pytest.raises(AssertionError, match='w = %s' % str(max_s + 1)):
        verify(max_msg, max_r, max_s + 1, stark_key)
    # Test invalid s length.
    with pytest.raises(AssertionError, match='s = %s' % str(max_s + 2)):
        verify(max_msg, max_r, max_s + 2, stark_key)


def test_ecdsa_signature():
    priv_key = get_random_private_key()
    public_key = private_key_to_ec_point_on_stark_curve(priv_key)
    msg = random.randint(0, 2**251 - 1)
    r, s = sign(msg, priv_key)
    assert verify(msg, r, s, public_key)
    assert verify(msg, r, s, public_key[0])
    assert not verify(msg + 1, r, s, public_key)
    assert not verify(msg + 1, r, s, public_key[0])
    assert not verify(msg, r + 1, s, public_key)
    assert not verify(msg, r + 1, s, public_key[0])
    assert not verify(msg, r, s + 1, public_key)
    assert not verify(msg, r, s + 1, public_key[0])


@pytest.fixture
def data_file() -> dict:
    json_file = os.path.join(os.path.dirname(__file__), 'signature_test_data.json')
    return json.load(open(json_file))


@pytest.fixture
def key_file() -> Dict[str, str]:
    json_file = os.path.join(os.path.dirname(__file__), 'keys_precomputed.json')
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


def test_order_message(data_file: dict):
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


def read_transfer_data(transfer_dict: dict) -> Dict[str, int]:
    """
    Transfers a dict of raw data representing a transfer, to an input dict for the
    `get_transfer_msg` function.
    """
    return {'amount': int(transfer_dict['amount']), 'nonce': int(transfer_dict['nonce']),
            'sender_vault_id': int(transfer_dict['sender_vault_id']),
            'token': int(transfer_dict['token'], 16),
            'receiver_vault_id': int(transfer_dict['target_vault_id']),
            'receiver_public_key': int(transfer_dict['target_public_key'], 16),
            'expiration_timestamp': transfer_dict['expiration_timestamp']}


def test_transfer_message(data_file: dict):
    """
    Tests transfer message. Parameters are from signature_test_data.json.
    """
    key = 'transfer_order'
    data = read_transfer_data(data_file[key])
    transfer_msg = get_transfer_msg(**data)

    assert transfer_msg == int(data_file['meta_data'][key]['message_hash'], 16)


def test_conditional_transfer_message(data_file: dict):
    """
    Tests conditional transfer message. Parameters are from signature_test_data.json.
    """
    key = 'conditional_transfer_order'
    data = read_transfer_data(data_file[key])
    conditional_transfer_msg = get_transfer_msg(
        condition=int(data_file[key]['condition'], 16), **data)

    assert conditional_transfer_msg == int(data_file['meta_data'][key]['message_hash'], 16)


@pytest.mark.parametrize('order_data', ['party_a_order', 'party_b_order'])
def test_limit_order_signing_example(data_file, order_data):
    """
    Tests signing limit order. Parameters are from signature_test_data.json.
    """
    msg_hash = int(data_file['meta_data'][order_data]['message_hash'], 16)
    order = data_file['settlement'][order_data]
    private_key = int(data_file['meta_data'][order_data]['private_key'], 16)
    public_key = private_to_stark_key(private_key)
    msg = get_limit_order_msg(
        vault_sell=int(order['vault_id_sell']), vault_buy=int(order['vault_id_buy']),
        amount_sell=int(order['amount_sell']), amount_buy=int(order['amount_buy']),
        token_sell=int(order['token_sell'], 16), token_buy=int(order['token_buy'], 16),
        nonce=int(order['nonce']),
        expiration_timestamp=order['expiration_timestamp'])
    r, s = sign(msg, private_key)

    assert(msg == msg_hash)
    assert(hex(r) == order['signature']['r'])
    assert(hex(s) == order['signature']['s'])
    assert verify(msg, r, s, public_key)


def test_transfer_signing_example(data_file: dict):
    """
    Tests signing transfer. Parameters are from signature_test_data.json.
    """
    private_key = int(data_file['meta_data']['party_a_order']['private_key'], 16)
    public_key = private_to_stark_key(private_key)
    key = 'transfer_order'
    data = read_transfer_data(data_file[key])
    transfer_msg = get_transfer_msg(**data)

    r, s = sign(transfer_msg, private_key)
    assert verify(transfer_msg, r, s, public_key)
    logger.info(f'transfer_msg signature: r: {r:x} s: {s:x}')


def test_conditional_transfer_signing_example(data_file: dict):
    """
    Tests signing conditional transfer. Parameters are from signature_test_data.json.
    """
    private_key = int(data_file['meta_data']['conditional_transfer_order']['private_key'], 16)
    public_key = private_to_stark_key(private_key)
    key = 'conditional_transfer_order'
    data = read_transfer_data(data_file[key])
    conditional_transfer_msg = get_transfer_msg(
        condition=int(data_file[key]['condition'], 16), **data)
    r, s = sign(conditional_transfer_msg, private_key)
    assert verify(conditional_transfer_msg, r, s, public_key)
    logger.info(f'conditional_transfer_msg signature: r: {r:x} s: {s:x}')


def test_pub_key_precomputed(key_file: Dict[str, str]):
    for private, public in key_file.items():
        assert public == hex(private_to_stark_key(int(private, 16)))


@pytest.fixture
def test_vector() -> dict:
    json_file = os.path.join(os.path.dirname(__file__), 'rfc6979_signature_test_vector.json')
    return json.load(open(json_file))


def test_rfc6979_signatures(test_vector: dict):
    """
    Test deterministic signing based on the RFC-6979 standard with a test vector common
    to several implementations
    """
    private_key = int(test_vector['private_key'], 16)
    public_key = private_to_stark_key(private_key)
    for message in test_vector['messages']:
        msg_hash = int(message['hash'], 16)
        expected_r = int(message['r'])
        expected_s = int(message['s'])
        real_r, real_s = sign(msg_hash, private_key)
        assert(expected_r == real_r)
        assert(expected_s == real_s)
        assert verify(msg_hash, real_r, real_s, public_key)


def test_signature_with_seed_works(test_vector: dict):
    """
    Test that the code produces a valid signature when there is a nonce given - so nothing
    breaks if we have to resample the randomness
    Also test that the signatures is different than the signature without a nonce,
    to make sure nonce affects the signature
    """
    private_key = int(test_vector['private_key'], 16)
    public_key = private_to_stark_key(private_key)
    for message in test_vector['messages']:
        msg_hash = int(message['hash'], 16)
        seedless_r = int(message['r'])
        seedless_s = int(message['s'])
        real_r, real_s = sign(msg_hash, private_key, seed=1)
        assert verify(msg_hash, real_r, real_s, public_key)
        assert not (real_r == seedless_r)
        assert not (real_s == seedless_s)
