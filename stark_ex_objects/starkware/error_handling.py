from enum import Enum
from typing import Optional


class StarkMsg(Enum):
    BAD_CONTRACTS_INFO = 0
    CONFLICTING_SETTLEMENT_AMOUNTS = 1
    INSUFFICIENT_ONCHAIN_BALANCE = 2
    INTERNAL = 3
    INVALID_BATCH_ID = 4
    INVALID_CLAIM_HASH = 5
    INVALID_COMMITTEE_MEMBER = 6
    INVALID_CONTRACT_ADDRESS = 7
    INVALID_FULFILLED_AMOUNT = 8
    INVALID_ORDER_ID = 9
    INVALID_ORDER_TYPE = 10
    INVALID_PACKAGE_ID = 11
    INVALID_REQUEST = 12
    INVALID_SETTLEMENT_RATIO = 13
    INVALID_SETTLEMENT_TOKENS = 14
    INVALID_SIGNATURE = 15
    INVALID_TRANSACTION_ID = 16
    INVALID_VAULT = 17
    MISMATCHING_ROOTS = 18
    ORDER_OVERDUE = 19
    OUT_OF_RANGE_BALANCE = 20
    OUT_OF_RANGE_BATCH_ID = 21
    OUT_OF_RANGE_DIFF = 22
    OUT_OF_RANGE_EXPIRATION_TIMESTAMP = 23
    OUT_OF_RANGE_NONCE = 24
    OUT_OF_RANGE_ORDER_ID = 25
    OUT_OF_RANGE_PUBLIC_KEY = 26
    OUT_OF_RANGE_TOKEN_ID = 27
    OUT_OF_RANGE_VAULT_ID = 28
    REQUEST_FAILED = 29
    SCHEMA_VALIDATION_ERROR = 30
    SUCCESS = 31
    TRANSACTION_PENDING = 32


class WebFriendlyException(Exception):
    def __init__(self, status_code, body):
        self.status_code = status_code
        self.body = body
        super().__init__(status_code, body)


class StarkException(WebFriendlyException):
    def __init__(self, code: StarkMsg, message: Optional[str] = None):
        self.code = code
        self.message = message
        super().__init__(status_code=500, body={'code': code, 'message': message})


def stark_assert(expr: bool, code: StarkMsg, message: Optional[str] = None):
    """
    Verifies that the given expression is True. If not, raises a StarkException with the given
    code and message.
    """
    if not expr:
        raise StarkException(code, message)


def stark_assert_eq(exp_val, actual_val, code: StarkMsg, message: Optional[str] = None):
    """
    Verifies that the the expected value is equal to the actual value, raising a StarkException with
    the appropriate code and message, where the expected and actual values are added to the message.
    """
    if exp_val != actual_val:
        eq_log = f'{exp_val} != {actual_val}'
        message = f'{message}\n{eq_log}' if message else eq_log
        raise StarkException(code, message)


def stark_assert_ne(exp_val, actual_val, code: StarkMsg, message: Optional[str] = None):
    """
    Verifies that the the expected value is not equal to the actual value, raising a StarkException
    with the appropriate code and message, where the expected and actual values are added to the
    message.
    """
    if exp_val == actual_val:
        eq_log = f'{exp_val} == {actual_val}'
        message = f'{message}\n{eq_log}' if message else eq_log
        raise StarkException(code, message)


def stark_assert_le(exp_val, actual_val, code: StarkMsg, message: Optional[str] = None):
    """
    Verifies that the the expected value is less than or equal to the actual value, raising a
    StarkException with the appropriate code and message, where the expected and actual values are
    added to the message.
    """
    if exp_val > actual_val:
        eq_log = f'{exp_val} > {actual_val}'
        message = f'{message}\n{eq_log}' if message else eq_log
        raise StarkException(code, message)


def stark_assert_lt(exp_val, actual_val, code: StarkMsg, message: Optional[str] = None):
    """
    Verifies that the the expected value is strictly less than the actual value, raising a
    StarkException with the appropriate code and message, where the expected and actual values are
    added to the message.
    """
    if exp_val >= actual_val:
        eq_log = f'{exp_val} >= {actual_val}'
        message = f'{message}\n{eq_log}' if message else eq_log
        raise StarkException(code, message)
