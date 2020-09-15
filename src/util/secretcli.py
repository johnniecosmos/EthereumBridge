from subprocess import run, PIPE
from typing import List

from src.contracts.secret_contract import burn_query


def sign_tx(unsigned_tx_path: str, multi_sig_account_addr: str, account_name: str):
    cmd = ['secretcli', 'tx', 'sign', unsigned_tx_path, '--signature-only', '--multisig',
           multi_sig_account_addr, '--from', account_name]

    return run_secret_cli(cmd)


def multisign_tx(unsigned_tx_path: str, multi_sig_account_name: str, *signed_tx):
    cmd = ['secretcli', 'tx', 'multisign', unsigned_tx_path, multi_sig_account_name] + list(signed_tx)

    return run_secret_cli(cmd)


def create_unsigined_tx(secret_contract_addr: str, encoded_args: str, chain_id: int, enclave_key: str,
                        code_hash: str, multisig_acc_addr: str) -> str:
    cmd = ['secretcli', 'tx', 'compute', 'execute', secret_contract_addr, f"'{encoded_args}'",
           '--generate-only', '--chain-id', f"{chain_id}", '--enclave-key', enclave_key, '--code-hash',
           code_hash, '--from', multisig_acc_addr]
    return run_secret_cli(cmd)


def broadcast(signed_tx_path: str) -> str:
    cmd = ['secretcli', 'tx', 'broadcast', signed_tx_path, '-b', 'block']
    return run_secret_cli(cmd)


def decrypt(data: str) -> str:
    cmd = ['secretcli', 'query', 'compute', 'decrypt', data]
    return run_secret_cli(cmd)


# TODO: test
def query_burn(nonce: int, contract_addr: str, viewing_key: str):
    query_str = burn_query(nonce, viewing_key)
    cmd = ['secretcli', 'query', 'compute', 'query', contract_addr, query_str]
    return run_secret_cli(cmd)


def run_secret_cli(cmd: List[str]) -> str:
    p = run(cmd, stdout=PIPE, stderr=PIPE)

    err = p.stderr
    if err:
        raise RuntimeError(err)

    return p.stdout.decode()
