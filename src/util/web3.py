from typing import Union

from eth_typing import HexStr, Hash32
from hexbytes import HexBytes
from web3 import Web3

# TODO: Use the auto detection of web3, will be good for docker setup
from src.contracts.secret_contract import tx_args
from src.util.secretcli import create_unsigined_tx


def web3_provider(address_: str) -> Web3:
    if address_.startswith('http'):  # HTTP
        return Web3(Web3.HTTPProvider(address_))
    elif address_.startswith('ws'):  # WebSocket
        return Web3(Web3.WebsocketProvider(address_))
    else:  # IPC
        return Web3(Web3.IPCProvider(address_))


def last_confirmable_block(provider: Web3, threshold: int = 12):
    latest_block = provider.eth.getBlock('latest')
    return latest_block.number - threshold


def extract_tx_by_address(address, block) -> list:
    return [tx for tx in block.transactions if tx.to and address.lower() == tx.to.lower()]


def event_log(tx_hash: Union[Hash32, HexBytes, HexStr], event: str, provider: Web3, contract):
    """
    Extracts logs of @event from tx_hash if present
    :param tx_hash:
    :param event: Case sensitive event name
    :param provider:
    :param contract: Web3 Contract
    :return: logs represented in 'AttributeDict' or 'None' if not found
    """
    receipt = provider.eth.getTransactionReceipt(tx_hash)
    logs = getattr(contract.events, event)().processReceipt(receipt)
    data_index = 0
    return logs[data_index] if logs else None


def normalize_address(address: str):
    # TODO: remove and check if all address is normalized in the api calls
    """Converts address to address acceptable by web3"""
    try:
        return Web3.toChecksumAddress(address.lower())
    except:
        return address


def generate_unsigned_tx(log, secret_contract_address: str, multisig_acc_addr: str):
    return create_unsigined_tx(secret_contract_address,
                               tx_args(log.args.amount, log.transactionHash.hex()),  # TODO:  log.args.to
                               multisig_acc_addr)
