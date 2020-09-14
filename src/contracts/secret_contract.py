import json


# TODO: talk about units(amount_seth)
def tx_args(amount, eth_tx_hash, recipient_address) -> str:
    return json.dumps({"mint": {"to": recipient_address, "amount_seth": amount, "eth_tx_hash": eth_tx_hash}})


# TODO: test
def burn_query(nonce: int, viewing_key: str) -> str:
    return json.dumps({"burn": {"nonce": nonce, "viewing_key": viewing_key}})
