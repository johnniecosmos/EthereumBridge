import json


from typing import Dict

# from typing import Dict
# from json import JSONDecodeError
# from src.util.secretcli import query_scrt_swap
# todo: move this here from inside the signer
# def swap_is_valid(secret_contract_addr: str, viewing_key: str, submission_data: Dict[str, any]) -> bool:
#     # lookup the tx hash in secret20, and validate it.
#     nonce = submission_data['nonce']
#     swap = query_scrt_swap(nonce, secret_contract_addr, viewing_key)
#
#     try:
#         swap_data = swap_query_res(swap)
#     except (AttributeError, JSONDecodeError) as e:
#         raise ValueError from e
#     if _check_tx_data(swap_data, submission_data):
#         return True
#     return False
#
#
# def _check_tx_data(swap_data: dict, submission_data: dict) -> bool:
#     """
#     This used to verify secret-20 <-> ether tx data
#     :param swap_data: the data from secret20 contract query
#     :param submission_data: the data from the proposed tx on the smart contract
#     """
#     return int(swap_data['amount']) == int(submission_data['value'])


def mint_json(amount, _, address: str) -> Dict:
    return {"mint": {"amount": str(amount), "address": address}}


def swap_json(nonce: int, viewing_key: str) -> str:
    return json.dumps({"swap": {"nonce": nonce, "viewing_key": viewing_key}})


def swap_query_res(res_json: str):
    return json.loads(res_json)['swap']['result']


def change_admin(address: str):
    return json.dumps({"change_admin": {"address": address}})
