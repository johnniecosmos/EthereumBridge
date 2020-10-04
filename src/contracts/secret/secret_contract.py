import json

from typing import Dict


def mint_json(amount, _, address: str) -> Dict:
    return {"mint": {"amount": str(amount), "address": address}}


def swap_json(nonce: int, viewing_key: str) -> str:
    return json.dumps({"swap": {"nonce": nonce, "viewing_key": viewing_key}})


def swap_query_res(res_json: str):
    return json.loads(res_json)['swap']['result']


def change_admin(address: str):
    return json.dumps({"change_admin": {"address": address}})
