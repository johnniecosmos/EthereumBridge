from contextlib import contextmanager
from logging import Logger
from typing import Union, List, Tuple, Optional, Generator

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
    return Web3.toChecksumAddress(address.lower())


# @contextmanager
def contract_event_in_range(logger: Logger, provider: Web3, contract, event: str, from_block: int = 0,
                            to_block: Optional[int] = None) -> Generator:
    """
    scans the blockchain, and yields blocks that has contract tx with the provided event

    Note: Be cautions with the range provided, as the logic creates query for each block which could be a bottleneck.
    :param from_block: starting block, defaults to 0
    :param to_block: end block, defaults to 'latest'
    :param event: name of the contract emit event you wish to be notified of
    """
    if to_block is None:
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
