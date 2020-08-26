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
