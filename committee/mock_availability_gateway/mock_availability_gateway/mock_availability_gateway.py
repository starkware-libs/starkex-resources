import asyncio
import datetime
import json
import logging
import logging.config
import os
import sys
import time

import yaml
from aiohttp import web

from starkware.error_handling import StarkMsg, stark_assert
from starkware.objects.availability import CommitteeSignature

logger = logging.getLogger(__package__)

DIR = os.path.dirname(__file__)


class MockAvailabilityGateway():
    """
    This is the StarkEx Services HTTP gateway for committee interactions.
    """

    def __init__(self):
        with open(os.path.join(DIR, 'data.json'), 'r') as json_file:
            self.data = json.load(json_file)

        self.batch_sent = {}
        self.batch_validated = {}

    async def is_alive(self, request):
        return web.Response(text='availability_gateway is alive!')

    async def get_batch_data(self, request):
        stark_assert(request.rel_url.query.keys() == {'batch_id'}, StarkMsg.INVALID_REQUEST)
        batch_id = request.rel_url.query['batch_id']
        logger.info(f'Got request for batch {batch_id}')
        stark_assert(batch_id.isdigit(), StarkMsg.INVALID_REQUEST, 'batch_id is not a number')

        batch_id = int(batch_id)
        batch_data_response = self.data[batch_id] if batch_id < len(self.data) else {'update': None}

        if batch_id in self.batch_sent and batch_id < len(self.data):
            logger.warn(f'Data for batch {batch_id} was requested more than once')
        else:
            self.batch_sent[batch_id] = time.time()

        return web.Response(text=json.dumps(batch_data_response))

    async def approve_new_roots(self, request):
        sig_data = CommitteeSignature.Schema().loads(await request.text())
        batch_id = sig_data.batch_id

        if batch_id in self.batch_validated:
            logger.warn(f'Signature for batch {batch_id} was sent more than once')
        else:
            self.batch_validated[batch_id] = time.time()
            request_time = self.batch_sent.get(batch_id)
            if request_time is None:
                logger.error(
                    f'Got signature for a batch {batch_id} which was not previously requested')
            else:
                elapsed_time = datetime.timedelta(
                    seconds=self.batch_validated[batch_id] - self.batch_sent[batch_id])
                logger.info(f'Got signature for batch {batch_id} after {elapsed_time} seconds')

        return web.Response(text='signature accepted')

    async def get_num_validated_batches(self, request):
        return web.Response(text=f'{len(self.batch_validated)}')


def start_server(availability_gateway):
    app = web.Application()
    app.add_routes([
        web.get('/availability_gateway/is_alive', availability_gateway.is_alive),
        web.get('/availability_gateway/get_batch_data', availability_gateway.get_batch_data),
        web.get('/availability_gateway/get_num_validated_batches',
                availability_gateway.get_num_validated_batches),
        web.post('/availability_gateway/approve_new_roots', availability_gateway.approve_new_roots)

    ])
    return app


async def make_app():
    availability_gateway = MockAvailabilityGateway()
    return start_server(availability_gateway)


async def main():
    config = yaml.safe_load(open('/config.yml', 'r'))
    logging.config.dictConfig(config.get('LOGGING', {}))
    app = await make_app()
    runner = web.AppRunner(app)
    try:
        await runner.setup()
        site = web.TCPSite(runner, None, 9414)
        await site.start()
        # This is a hack as after calling site.start(), it doesn't wait that the app will finish.
        while True:
            await asyncio.sleep(1)
    finally:
        await runner.cleanup()

if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
