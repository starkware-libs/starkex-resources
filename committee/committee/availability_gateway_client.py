import logging
from typing import Optional
from urllib.parse import urljoin

import requests

from starkware.objects.availability import BatchDataResponse, CommitteeSignature, StateUpdate

logger = logging.getLogger(__package__)


class BadRequest(Exception):
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text

    def __repr__(self):
        return f'HTTP error ocurred. Status: {str(self.status_code)}.' + \
            f' Text: {self.text}'


class AvailabilityGatewayClient:
    def __init__(self, gateway_url='http://localhost:9414/', requests_kwargs={}):
        self.gateway_url = gateway_url
        self.requests_kwargs = requests_kwargs

    def _send_request(self, send_method, uri, data=None):
        url = urljoin(self.gateway_url, uri)
        res = requests.request(send_method, url, data=data, **self.requests_kwargs)
        if res.status_code != 200:
            raise BadRequest(res.status_code, res.text)
        return res.text

    async def get_batch_data(self, batch_id: int) -> Optional[StateUpdate]:
        uri = f'/availability_gateway/get_batch_data?batch_id={batch_id}'
        answer = self._send_request('GET', uri)

        return BatchDataResponse.Schema().loads(answer).update

    async def send_signature(self, batch_id: int, sig: str, member_key: str, claim_hash: str):
        encoded_signature = CommitteeSignature.Schema().dumps(CommitteeSignature(
            batch_id=batch_id, signature=sig, member_key=member_key, claim_hash=claim_hash))

        answer = self._send_request(
            'POST', f'/availability_gateway/approve_new_roots', data=encoded_signature)

        if answer != 'signature accepted':
            logger.error(f'unexpected response: {answer}')
            assert False, 'Signature was not accepted'

        logger.debug(f'Signature for batch {batch_id} was sent successfully')
