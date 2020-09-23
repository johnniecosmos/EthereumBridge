from logging import Logger
from typing import Union, List, Tuple, Optional

from eth_typing import HexStr, Hash32
from hexbytes import HexBytes
from web3 import Web3
from web3.contract import Contract as Web3Contract
from web3.datastructures import AttributeDict
from web3.types import BlockData


def web3_provider(address_: str) -> Web3:
    if address_.startswith('http'):  # HTTP
        return Web3(Web3.HTTPProvider(address_))
    elif address_.startswith('ws'):  # WebSocket
        return Web3(Web3.WebsocketProvider(address_))
    else:  # IPC
        return Web3(Web3.IPCProvider(address_))


def extract_tx_by_address(address, block: BlockData) -> list:
    # Note: block attribute dict has to be generated with full_transactions=True flag
    return [tx for tx in block.transactions if tx.to and address.lower() == tx.to.lower()]


def event_log(tx_hash: Union[Hash32, HexBytes, HexStr], events: List[str], provider: Web3, contract: Web3Contract) -> \
        Tuple[str, Optional[AttributeDict]]:
    """
    Extracts logs of @event from tx_hash if present
    :param tx_hash:
    :param events: Case sensitive events name
    :param provider:
    :param contract: Web3 Contract
    :return: event name and log represented in 'AttributeDict' or 'None' if not found
    """
    receipt = provider.eth.getTransactionReceipt(tx_hash)
    for event in events:
        log = getattr(contract.events, event)().processReceipt(receipt)
        if log:
            data_index = 0
            return event, log[data_index]
    return '', None


def normalize_address(address: str):
    """Converts address to address acceptable by web3"""
    try:
        return Web3.toChecksumAddress(address.lower())
    except:
        return address


def contract_event_in_range(logger: Logger, provider: Web3, contract, event: str, from_block: int = 0,
                            to_block: Union[int, str] = 'latest'):
    """
    scans the blockchain, and yields blocks that has contract tx with the provided event

    Note: Be cautions with the range provided, as the logic creates query for each block which could be a buttel neck.
    :param from_block: starting block, defaults to 0
    :param to_block: end block, defaults to 'latest'
    :param event: name of the contract emit event you wish to be notified of
    """
    if to_block == 'latest':
        to_block = provider.eth.getBlock('latest').number

    for block_num in range(from_block, to_block + 1):
        try:
            block = provider.eth.getBlock(block_num, full_transactions=True)
            contract_transactions = extract_tx_by_address(contract.address, block)

            if not contract_transactions:
                continue

            for tx in contract_transactions:
                _, log = event_log(tx_hash=tx.hash, events=[event], provider=provider, contract=contract.contract)

                if log is None:
                    continue

                yield log
        except Exception as e:
            logger.error(msg=e)
    raise StopIteration()


def send_contract_tx(provider: Web3, contract: Web3Contract, function_name: str, from_acc: str, private_key: bytes,
                     *args, gas: int = 0):
    """ Creates the contract tx and signs it with private_key to be transmitted as raw tx """
    submit_tx = getattr(contract.functions, function_name)(*args). \
        buildTransaction(
        {
            'from': from_acc,
            'chainId': provider.eth.chainId,
            'gasPrice': provider.eth.gasPrice if not gas else gas,
            'nonce': provider.eth.getTransactionCount(from_acc),
        })
    signed_txn = provider.eth.account.sign_transaction(submit_tx, private_key)
    provider.eth.sendRawTransaction(signed_txn.rawTransaction)


# noinspection PyPep8Naming
def decode_encodeAbi(data: bytes) -> Tuple[str, int]:
    """
    This functions takes a chunk of data encoded by web3 contract encodeAbi func and extracts the params from it.
    :param data: an encodeAbi result
    """
    method_id, dest, amount = data[:10], data[34:74], data[74:]
    return '0x' + dest.decode(), int(amount, 16)  # convert amount for hex to decimal

# b'0xa9059cbb000000000000000000000000e6ec7f8934f95e0ebbca62ad344e3892c96187eb0000000000000000000000000000000000000000000000000000000000000064'
# @combomethod
# def decode_function_input(self, data: HexStr) -> Tuple['ContractFunction', Dict[str, Any]]:
#     # type ignored b/c expects data arg to be HexBytes
#     data = HexBytes(data)  # type: ignore
#     selector, params = data[:4], data[4:]
#     func = self.get_function_by_selector(selector)
#
#     names = get_abi_input_names(func.abi)
#     types = get_abi_input_types(func.abi)
#
#     decoded = self.web3.codec.decode_abi(types, cast(HexBytes, params))
#     normalized = map_abi_data(BASE_RETURN_NORMALIZERS, types, decoded)
#
#     return func, dict(zip(names, normalized))
