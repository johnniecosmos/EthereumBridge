import json

from src.config import secret_contract_address


def tx_args(amount, eth_tx_hash):
    return json.dumps({"mint": {"to": secret_contract_address, "amount_seth": amount, "eth_tx_hash": eth_tx_hash}})
