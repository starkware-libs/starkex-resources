import re

from marshmallow import fields


class IntAsStr(fields.Field):
    """
    A field that behaves like an integer, but serializes to a string. Some amount field are
    serialized to string in the jsons, so that javascript can handle them - javascript cannot handle
    uint64 numbers.
    """

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        return str(value)

    def _deserialize(self, value, attr, data, **kwargs):
        return int(value)


class EnumField(fields.Field):
    """
    A field that behaves like an enum, but serializes to a string.
    """

    def __init__(self, enum_cls, required: bool = False):
        self.enum_cls = enum_cls
        super().__init__(required=required)

    def _serialize(self, value, attr, obj, **kwargs):
        return value.name

    def _deserialize(self, value, attr, data, **kwargs):
        return self.enum_cls[value]


class IntAsHex(fields.Field):
    """
    A field that behaves like an integer, but serializes to hex string. Usually, this applies to
    field elements.
    """

    default_error_messages = {'invalid': 'Expected hex string, got: "{input}".'}

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        assert isinstance(value, int)
        return hex(value)

    def _deserialize(self, value, attr, data, **kwargs):
        if re.match('^0x[0-9a-f]+$', value) is None:
            self.fail('invalid', input=value)

        return int(value, 16)


class BytesAsHex(fields.Field):
    """
    A field that behaves like bytes, but serializes to hex string.
    """

    default_error_messages = {'invalid': 'Expected hex string, got: "{input}".'}

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        assert isinstance(value, bytes)
        return value.hex()

    def _deserialize(self, value, attr, data, **kwargs):
        if re.match('^[0-9a-f]+$', value) is None:
            self.fail('invalid', input=value)

        return bytes.fromhex(value)
