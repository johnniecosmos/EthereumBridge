import json
from os import path
from subprocess import run, PIPE
from typing import Dict


def get_key_signer(key_name: str, keys_dir: str) -> Dict:
    with open(path.join(keys_dir, key_name + ".json"), "r") as f:
        return json.load(f)


def get_key_multisig_addr(key_name: str) -> str:
    p = run(('secretcli', 'keys', 'list'), stdout=PIPE, stderr=PIPE)
    res = ''
    for key in filter(lambda x: x['name'] == key_name, json.loads(p.stdout)):
        res = key['address']
    if not res:
        raise RuntimeError(f"No key account with required name: {key_name}")
    return res


def get_viewing_key(a_address: str, secret_contract_address: str) -> str:
    # get view key
    json_q = '{"create_viewing_key": {"entropy": "random phrase"}}'
    view_key_tx_hash = run(f"docker exec secretdev secretcli tx compute execute {secret_contract_address} "
                           f"'{json_q}' --from {a_address} --gas 3000000 -b block -y | jq '.txhash'",
                           shell=True, stdout=PIPE)
    view_key_tx_hash = view_key_tx_hash.stdout.decode().strip()[1:-1]
    view_key = run(f"docker exec secretdev secretcli q compute tx {view_key_tx_hash} | jq '.output_log' | "
                   f"jq '.[0].attributes[1].value'", shell=True, stdout=PIPE).stdout.decode().strip()[1:-1]
    return view_key
