from subprocess import run, PIPE
from typing import List


# Note: tx accepted in this module are valid file path or valid json string

def sign_tx(unsigned_tx: str, multi_sig_account_addr: str, account_name: str):
    cmd = ['secretcli', 'tx', 'sign', unsigned_tx, '--signature-only', '--multisig',
           multi_sig_account_addr, '--from', account_name]

    return run_secret_cli(cmd)


def multisign_tx(unsigned_tx: str, multi_sig_account_name: str, *signed_tx):
    cmd = ['secretcli', 'tx', 'multisign', f"'{unsigned_tx}'", multi_sig_account_name] + \
          list(map(lambda tx: f"'tx'", signed_tx))

    return run_secret_cli(cmd)


def create_unsigined_tx(secret_contract_addr: str, encoded_args: str, chain_id: int, enclave_key: str,
                        enclave_hash: str, multisig_acc_addr: str) -> str:
    cmd = ['secretcli', 'tx', 'compute', 'execute', secret_contract_addr, f"'{encoded_args}'",
           '--generate-only', '--chain-id', f"{chain_id}", '--enclave-key', enclave_key, '--code-hash',
           enclave_hash, '--from', multisig_acc_addr]
    return run_secret_cli(cmd)


def broadcast(signed_tx: str) -> str:
    cmd = ['secretcli', 'tx', 'broadcast', f"'{signed_tx}'"]
    return run_secret_cli(cmd)


def decrypt(data: str) -> str:
    cmd = ['secretcli', 'query', 'compute', 'decrypt', data]
    return run_secret_cli(cmd)


def run_secret_cli(cmd: List[str]) -> str:
    p = run(tuple(cmd), stdout=PIPE, stderr=PIPE)

    err = p.stderr
    if err:
        raise RuntimeError(err.decode())

    return p.stdout.decode()
