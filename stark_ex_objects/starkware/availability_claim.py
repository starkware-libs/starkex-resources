from web3 import Web3


def hash_availability_claim(
        vaults_root: bytes, vaults_height: int, trades_root: bytes, trades_height: int,
        seq_num: int):
    """
    Prepares the availability claim that the committee signs.
    Hashes the inputs in the format required for the data availability Contract.
    """
    return Web3.solidityKeccak(
        ['bytes32', 'uint256', 'bytes32', 'uint256', 'uint256'],
        [vaults_root, vaults_height, trades_root, trades_height, seq_num])
