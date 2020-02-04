import argparse
import json
import os

from committee.availability_gateway_client import AvailabilityGatewayClient
from starkware.objects.availability import BatchDataResponse

DIR = os.path.dirname(__file__)


def main():
    """
    Fetches StateUpdate records from a StarkEx AvailabilityGateway and dumps them to a file.
    """
    parser = argparse.ArgumentParser(description='Presubmit script.')

    parser.add_argument('--gateway_url', type=str, default='http://localhost:9414')
    parser.add_argument('--filename', type=str, default=os.path.join(DIR, 'data.json'))
    parser.add_argument('--n_batches', type=int, default=6,
                        help='Number of batchs to fetch')
    args = parser.parse_args()

    client = AvailabilityGatewayClient()

    updates_list = []
    for batch_id in range(args.n_batches):
        info = client.get_batch_data(batch_id)
        assert info is not None, f'batch {batch_id} is not availabile'
        updates_list.append(info)

    with open(args.filename, 'w') as json_file:
        json.dump(BatchDataResponse.Schema().dump(updates_list, many=True), json_file, indent=4)
        json_file.write('\n')


main()
