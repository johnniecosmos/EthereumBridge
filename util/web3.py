import json

from web3 import Web3


# TODO: Use the auto detection of web3, will be good for docker setup
def web3_provider(address_: str) -> Web3:
    if address_.startswith('http'):  # HTTP
        return Web3(Web3.HTTPProvider(address_))
    elif address_.startswith('ws'):  # WebSocket
        return Web3(Web3.WebsocketProvider(address_))
    else:  # IPC
        return Web3(Web3.IPCProvider(address_))


def unsigned_tx(contract: str = "0xabcdefg...", recipient: str = "0xABCDEFG...", amount: int = 1):
    return json.dumps({"contract": contract, "recipient": recipient, "amount": amount})


def last_confirmable_block(provider: Web3, threshold: int = 12):
    latest_block = provider.eth.getBlock('latest')
    return latest_block.number - threshold


def extract_tx_by_address(address, block) -> list:
    res = []
    for tx in block.transactions:
        if address == tx.to:
            res.append(tx)

    return res
