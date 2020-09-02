import json


def tx_args(amount, eth_tx_hash, recipient_address):
    return json.dumps({"mint": {"to": recipient_address, "amount_seth": amount, "eth_tx_hash": eth_tx_hash}})
