import random

from starkware.crypto.signature import EC_ORDER, pedersen_hash

from .fast_pedersen_hash import HASH_SHIFT_POINT, pedersen_hash_func


def test_zero_element():
    zero = int(0).to_bytes(32, 'big')
    assert pedersen_hash_func(zero, zero) == HASH_SHIFT_POINT.x.to_bytes(32, 'big')


def test_random_hash():
    x = random.randint(0, EC_ORDER - 1)
    y = random.randint(0, EC_ORDER - 1)

    expected_res = pedersen_hash(x, y).to_bytes(32, 'big')

    assert expected_res == pedersen_hash_func(x.to_bytes(32, 'big'), y.to_bytes(32, 'big'))
