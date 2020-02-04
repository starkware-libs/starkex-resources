import codecs
from typing import Optional

from botocore.exceptions import ClientError

from .storage import Storage


class S3Storage(Storage):
    """
    Storage for S3.
    Example usage:
      session = aiobotocore.get_session()
      client = session.create_client('s3')
      storage = S3Storage(client)
    """

    def __init__(self, client, bucket: str, prefix: str):
        self.client = client
        self.bucket = bucket
        self.prefix = prefix

    @staticmethod
    def escape(key: bytes) -> str:
        return codecs.escape_encode(key)[0].decode('ascii')  # type: ignore

    async def set_value(self, key: bytes, value: bytes):
        assert isinstance(key, bytes)
        assert isinstance(value, bytes)
        await self.client.put_object(Bucket=self.bucket,
                                     Key=self.prefix + '/' + S3Storage.escape(key),
                                     Body=value)

    async def get_value(self, key: bytes) -> Optional[bytes]:
        assert isinstance(key, bytes)
        try:
            res = await self.client.get_object(Bucket=self.bucket,
                                               Key=self.prefix + '/' + S3Storage.escape(key))
            return await res['Body'].read()
        except ClientError:
            return None

    async def del_value(self, key: bytes):
        assert isinstance(key, bytes)
        await self.client.delete_object(Bucket=self.bucket,
                                        Key=self.prefix + '/' + S3Storage.escape(key))

    def get_path_from_key(self, key: bytes) -> str:
        assert isinstance(key, bytes)
        return f'{self.prefix}/{S3Storage.escape(key)}'
