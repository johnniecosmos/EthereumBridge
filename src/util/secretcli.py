from logging import Logger
from subprocess import run, PIPE
from typing import List, Tuple

from src.contracts.secret_contract import scrt_swap_query


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


def query_scrt_swap(logger: Logger, nonce: int, contract_addr: str, viewing_key: str) -> Tuple[str, bool]:
    query_str = scrt_swap_query(nonce, viewing_key)
    cmd = ['secretcli', 'query', 'compute', 'query', contract_addr, query_str]
    p = run(cmd, stdout=PIPE, stderr=PIPE)

    if p.stderr:
        if 'ERROR: query result: encrypted: Tx does not exist' not in p.stderr.decode():
            logger.error(msg=p.stderr.decode())
        return '', False
    
    return p.stdout.decode(), True


def run_secret_cli(cmd: List[str]) -> str:
    p = run(cmd, stdout=PIPE, stderr=PIPE)

    err = p.stderr
    if err:
        raise RuntimeError(err)

    return p.stdout.decode()
