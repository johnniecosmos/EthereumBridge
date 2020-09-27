import json


# TODO: talk about units(amount_seth)
from typing import Dict


def mint_json(amount, eth_tx_hash, address: str) -> Dict:
    return {"mint": {"amount": str(amount), "address": address}}


def swap_json(nonce: int, viewing_key: str) -> str:
    return json.dumps({"swap": {"nonce": nonce, "viewing_key": viewing_key}})


def swap_query_res(res_json: str):
    return json.loads(res_json)['swap']['result']
