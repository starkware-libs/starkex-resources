import json
import os

import pytest

from starkware.crypto.signature.fast_pedersen_hash import async_pedersen_hash_func
from starkware.objects.availability import BatchDataResponse
from starkware.storage.test_utils import MockStorage

from .committee import Committee


ORDER_TREE_HEIGHT = 63


class AvailabilityGatewayClientMock:
    def __init__(self):
        pass

    async def order_tree_height(self) -> int:
        return ORDER_TREE_HEIGHT


@pytest.fixture
def committee():
    config = {
        'VAULTS_MERKLE_HEIGHT': 31,
        'ORDERS_MERKLE_HEIGHT': ORDER_TREE_HEIGHT,
        'POLLING_INTERVAL': 1,
    }

    return Committee(
        config=config,
        private_key='0xbfb1d570ddf495e378a1a85140e72d177a92637223fa540e05aaa061179f4290',
        storage=MockStorage(),
        merkle_storage=MockStorage(),
        hash_func=async_pedersen_hash_func,
        availability_gateway=AvailabilityGatewayClientMock())


@pytest.fixture
def state_update():
    # batch_info.json is the batch availability data for batch-0 from end_to_end_test.
    # To generate this file:
    # - Run end_to_end_test.
    # - While the test is running, use curl to call get_batch_data for batch_id 0:
    #   curl localhost:9414/availability_gateway/get_batch_data?batch_id=0
    # - Save the response.
    batch_info_file = os.path.join(os.path.dirname(__file__), 'batch_info.json')
    with open(batch_info_file) as fp:
        batch_info = fp.read()
    state_update = BatchDataResponse.Schema().loads(batch_info).update
    return state_update


@pytest.fixture
def expected_signature():
    # The expected signature on the roots in the used config file.
    return '0xbfaa70666e1dcb21fe92014e4f0b8ff263a582b592855a7fd566d7f468aea0457' \
        '26663fbf723fc53ad33dbb949c72030fbd38bbed05ca53aebbe1b03043fe72e1b'


@pytest.mark.asyncio
async def test_initialization(committee):
    """
    Test committee initialization.
    """
    assert await committee.storage.get_value(committee.committee_batch_info_key(-1)) is None
    assert await committee.storage.get_int(Committee.next_batch_id_key()) is None
    await committee.compute_initial_batch_info()
    batch_info = json.loads(
        await committee.storage.get_value(committee.committee_batch_info_key(-1)))
    assert batch_info['sequence_number'] == -1
    assert batch_info['vaults_root'] == \
        '0075364111a7a336756626d19fc8ec8df6328a5e63681c68ffaa312f6bf98c5c'
    assert batch_info['orders_root'] == \
        '01bb0b0bdb803c733cf692a324a31e8e7749a9fdfb597d74e71c604795e659ed'


@pytest.mark.asyncio
@pytest.mark.parametrize('validate_orders', [True, False])
@pytest.mark.parametrize('valid_vault_root', [True, False])
@pytest.mark.parametrize('valid_order_root', [True, False])
async def test_validate_data_availability(committee, state_update, expected_signature,
                                          validate_orders, valid_vault_root, valid_order_root):
    """
    Test committee validate_data_availability().
    """
    await committee.compute_initial_batch_info()

    # Corrupt vault data if needed.
    if not valid_vault_root:
        state_update.vaults.popitem()

    # Corrupt order data if needed.
    if not valid_order_root:
        state_update.orders.popitem()

    if (not valid_vault_root) or (validate_orders and not valid_order_root):
        with pytest.raises(AssertionError, match='root mismatch'):
            await committee.validate_data_availability(0, state_update, validate_orders)

    else:
        signature, _ = await committee.validate_data_availability(0, state_update, validate_orders)
        assert signature == expected_signature
