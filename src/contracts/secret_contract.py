import json


# TODO: talk about units(amount_seth)
def mint_json(amount, eth_tx_hash, address) -> str:
    return json.dumps({"mint": {"amount": str(amount), "address": address}})


def scrt_swap_query(nonce: int, viewing_key: str) -> str:
    return json.dumps({"swap": {"nonce": nonce, "viewing_key": viewing_key}})
