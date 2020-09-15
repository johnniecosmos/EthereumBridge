import json


# TODO: talk about units(amount_seth)
def unsigned_mint_tx(amount, eth_tx_hash, recipient_address) -> str:
    return json.dumps({"mint": {"to": recipient_address, "amount_seth": amount, "eth_tx_hash": eth_tx_hash}})


def scrt_swap_query(nonce: int, viewing_key: str) -> str:
    return json.dumps({"swap": {"nonce": nonce, "viewing_key": viewing_key}})
