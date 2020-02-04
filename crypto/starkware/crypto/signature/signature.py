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
import math
import os
import random

from .math_utils import div_mod, ec_add, ec_double, ec_mult, is_quad_residue, sqrt_mod

PEDERSEN_HASH_POINT_FILENAME = os.path.join(
    os.path.dirname(__file__), 'pedersen_params.json')
PEDERSEN_PARAMS = json.load(open(PEDERSEN_HASH_POINT_FILENAME))

FIELD_PRIME = PEDERSEN_PARAMS['FIELD_PRIME']
FIELD_GEN = PEDERSEN_PARAMS['FIELD_GEN']
ALPHA = PEDERSEN_PARAMS['ALPHA']
BETA = PEDERSEN_PARAMS['BETA']
EC_ORDER = PEDERSEN_PARAMS['EC_ORDER']
CONSTANT_POINTS = PEDERSEN_PARAMS['CONSTANT_POINTS']

N_ELEMENT_BITS_ECDSA = math.floor(math.log(FIELD_PRIME, 2))
assert N_ELEMENT_BITS_ECDSA == 251

N_ELEMENT_BITS_HASH = math.ceil(math.log(FIELD_PRIME, 2))
assert N_ELEMENT_BITS_HASH == 252

# Elliptic curve parameters.
assert 2**N_ELEMENT_BITS_ECDSA < EC_ORDER < FIELD_PRIME

SHIFT_POINT = CONSTANT_POINTS[0]
MINUS_SHIFT_POINT = [SHIFT_POINT[0], FIELD_PRIME - SHIFT_POINT[1]]
EC_GEN = CONSTANT_POINTS[1]

assert SHIFT_POINT == [0x49ee3eba8c1600700ee1b87eb599f16716b0b1022947733551fde4050ca6804,
                       0x3ca0cfe4b3bc6ddf346d49d06ea0ed34e621062c0e056c1d0405d266e10268a]
assert EC_GEN == [0x1ef15c18599971b7beced415a40f0c7deacfd9b0d1819e03d723d8bc943cfca,
                  0x5668060aa49730b7be4801df46ec62de53ecd11abe43a32873000c36e8dc1f]


#########
# ECDSA #
#########


class InvalidPublicKeyError(Exception):
    def __init__(self):
        super().__init__('Given x coordinate does not represent any point on the elliptic curve.')


def get_y_coordinate(stark_key_x_coordinate):
    """
    Given the x coordinate of a stark_key, returns a possible y coordinate such that together the
    point (x,y) is on the curve.
    Note that the real y coordinate is either y or -y.
    If x is invalid stark_key it throws an error.
    """

    x = stark_key_x_coordinate
    y_squared = (x * x * x + ALPHA * x + BETA) % FIELD_PRIME
    if not is_quad_residue(y_squared, FIELD_PRIME):
        raise InvalidPublicKeyError()
    return sqrt_mod(y_squared, FIELD_PRIME)


def get_random_private_key():
    # NOTE: It is IMPORTANT to use a strong random function here.
    return random.randint(1, EC_ORDER - 1)


def private_key_to_ec_point_on_stark_curve(priv_key):
    assert 0 < priv_key < EC_ORDER
    return ec_mult(priv_key, EC_GEN, ALPHA, FIELD_PRIME)


def private_to_stark_key(priv_key):
    return private_key_to_ec_point_on_stark_curve(priv_key)[0]


def sign(msg_hash, priv_key):
    # Note: msg_hash must be smaller than 2**N_ELEMENT_BITS_ECDSA.
    # Message whose hash is >= 2**N_ELEMENT_BITS_ECDSA cannot be signed.
    # This happens with a very small probability.
    assert 0 <= msg_hash < 2**N_ELEMENT_BITS_ECDSA, 'Message not signable.'

    # Choose a valid k. In our version of ECDSA not every k value is valid,
    # and there is a negligible probability a drawn k cannot be used for signing.
    # This is why we have this loop.
    while True:
        # NOTE: It is IMPORTANT to use a strong random function here
        # or use a similar technique as in RFC6979
        # (pseudo-random defined by hash and secret-key).
        k = random.randint(1, EC_ORDER - 1)

        # Cannot fail because 0 < k < EC_ORDER and EC_ORDER is prime.
        x = ec_mult(k, EC_GEN, ALPHA, FIELD_PRIME)[0]

        # DIFF: in classic ECDSA, we take int(x) % n.
        r = int(x)
        if not (1 <= r < 2**N_ELEMENT_BITS_ECDSA):
            # Bad value. This fails with negligible probability.
            continue

        if (msg_hash + r * priv_key) % EC_ORDER == 0:
            # Bad value. This fails with negligible probability.
            continue

        w = div_mod(k, msg_hash + r * priv_key, EC_ORDER)
        if not (1 <= w < 2**N_ELEMENT_BITS_ECDSA):
            # Bad value. This fails with negligible probability.
            continue

        # DIFF: Here we send w instead of its inverse.
        return r, w


def mimic_ec_mult_air(m, point, shift_point):
    """
    Computes m * point + shift_point using the same steps like the AIR and throws an exception if
    and only if the AIR errors.
    """
    assert 0 < m < 2**N_ELEMENT_BITS_ECDSA
    partial_sum = shift_point
    for _ in range(N_ELEMENT_BITS_ECDSA):
        assert partial_sum[0] != point[0]
        if m & 1:
            partial_sum = ec_add(partial_sum, point, FIELD_PRIME)
        point = ec_double(point, ALPHA, FIELD_PRIME)
        m >>= 1
    assert m == 0
    return partial_sum


def verify(msg_hash, r, w, public_key):
    # Preassumptions:
    # DIFF: in classic ECDSA, we assert 1 <= r, w <= EC_ORDER-1.
    # Since r, w < 2**N_ELEMENT_BITS_ECDSA < EC_ORDER, we only need to verify r, w != 0.
    assert 1 <= r < 2**N_ELEMENT_BITS_ECDSA, 'r = %s' % r
    assert 1 <= w < 2**N_ELEMENT_BITS_ECDSA, 'w = %s' % w
    assert 0 <= msg_hash < 2**N_ELEMENT_BITS_ECDSA

    if isinstance(public_key, int):
        # Only the x coordinate of the point is given, check the two possibilities for the y
        # coordinate.
        try:
            y = get_y_coordinate(public_key)
        except InvalidPublicKeyError:
            return False
        assert pow(y, 2, FIELD_PRIME) == (
            pow(public_key, 3, FIELD_PRIME) + ALPHA * public_key + BETA) % FIELD_PRIME
        return verify(msg_hash, r, w, (public_key, y)) or \
            verify(msg_hash, r, w, (public_key, (-y) % FIELD_PRIME))
    else:
        # The public key is provided as a point.
        # Verify it is on the curve.
        assert (public_key[1]**2 - (public_key[0]**3 + ALPHA *
                                    public_key[0] + BETA)) % FIELD_PRIME == 0

    # Signature validation.
    # DIFF: original formula is:
    # x = (w*msg_hash)*EC_GEN + (w*r)*public_key
    # While what we implement is:
    # x = w*(msg_hash*EC_GEN + r*public_key).
    # While both mathematically equivalent, one might error while the other doesn't,
    # given the current implementation.
    # This formula ensures that if the verification errors in our AIR, it errors here as well.
    try:
        zG = mimic_ec_mult_air(msg_hash, EC_GEN, MINUS_SHIFT_POINT)
        rQ = mimic_ec_mult_air(r, public_key, SHIFT_POINT)
        wB = mimic_ec_mult_air(w, ec_add(zG, rQ, FIELD_PRIME), SHIFT_POINT)
        x = ec_add(wB, MINUS_SHIFT_POINT, FIELD_PRIME)[0]
    except AssertionError:
        return False

    # DIFF: Here we drop the mod n from classic ECDSA.
    return r == x


#################
# Pedersen hash #
#################

def pedersen_hash(*elements):
    return pedersen_hash_as_point(*elements)[0]


def pedersen_hash_as_point(*elements):
    """
    Similar to pedersen_hash but also returns the y coordinate of the resulting EC point.
    This function is used for testing.
    """
    point = SHIFT_POINT
    for i, x in enumerate(elements):
        assert 0 <= x < FIELD_PRIME
        point_list = CONSTANT_POINTS[2 + i * N_ELEMENT_BITS_HASH:2 + (i + 1) * N_ELEMENT_BITS_HASH]
        assert len(point_list) == N_ELEMENT_BITS_HASH
        for pt in point_list:
            assert point[0] != pt[0], 'Unhashable input.'
            if x & 1:
                point = ec_add(point, pt, FIELD_PRIME)
            x >>= 1
        assert x == 0
    return point

#############################
# party_a/party_b signature #
#############################


def get_msg(instruction_type, vault0, vault1, amount0, amount1, token0,
            token1_or_pub_key, nonce, expiration_timestamp, hash=pedersen_hash):
    """
    Creates a message to sign on.
    """
    packed_message = instruction_type
    packed_message = packed_message * 2**31 + vault0
    packed_message = packed_message * 2**31 + vault1
    packed_message = packed_message * 2**63 + amount0
    packed_message = packed_message * 2**63 + amount1
    packed_message = packed_message * 2**31 + nonce
    packed_message = packed_message * 2**22 + expiration_timestamp
    return hash(hash(token0, token1_or_pub_key), packed_message)


def get_limit_order_msg(vault_sell, vault_buy, amount_sell, amount_buy, token_sell,
                        token_buy, nonce, expiration_timestamp, hash=pedersen_hash):
    """
    party_a sells amount_sell coins of token_sell from vault_sell.
    party_a buys amount_buy coins of token_buy into vault_buy.
    """
    assert 0 <= vault_sell < 2**31
    assert 0 <= vault_buy < 2**31
    assert 0 <= amount_sell < 2**63
    assert 0 <= amount_buy < 2**63
    assert 0 <= token_sell < FIELD_PRIME
    assert 0 <= token_buy < FIELD_PRIME
    assert 0 <= nonce < 2**31
    assert 0 <= expiration_timestamp < 2**22

    instruction_type = 0
    return get_msg(instruction_type, vault_sell, vault_buy, amount_sell, amount_buy, token_sell,
                   token_buy, nonce, expiration_timestamp, hash=hash)


def get_transfer_msg(amount, nonce, sender_vault_id, token, receiver_vault_id,
                     receiver_public_key, expiration_timestamp, hash=pedersen_hash):
    """
    Transfer `amount` of `token` from `sender_vault_id` to `receiver_vault_id`.
    """
    assert 0 <= sender_vault_id < 2**31
    assert 0 <= receiver_vault_id < 2**31
    assert 0 <= amount < 2**63
    assert 0 <= token < FIELD_PRIME
    assert 0 <= receiver_public_key < FIELD_PRIME
    assert 0 <= nonce < 2**31
    assert 0 <= expiration_timestamp < 2**22

    instruction_type = 1
    return get_msg(instruction_type, sender_vault_id, receiver_vault_id, amount, 0, token,
                   receiver_public_key, nonce, expiration_timestamp, hash=hash)
