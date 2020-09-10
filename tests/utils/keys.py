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
