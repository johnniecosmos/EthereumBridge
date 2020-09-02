from subprocess import run, PIPE
from pathlib import Path
from os import name
from typing import List

from src.config import secret_cli, enclave_hash, enclave_key, chain_id

if name == 'nt':
    bash = [r"C:\Program Files\Git\bin\bash.exe", "-c"]
else:
    bash = []


def sign_tx(unsigned_tx: str, multi_sig_account_addr: str, account_name: str):
    secret_cli_posix = Path(secret_cli).as_posix()
    unsigned_tx_posix = Path(unsigned_tx).as_posix()
    cmd = ['SGX_MODE=SW', 'secretcli', 'tx', 'sign', unsigned_tx_posix, '--signature-only', '--multisig',multi_sig_account_addr,
           '--from', account_name]
    return run_secret_cli(cmd)
    # return run_secret_cli(" ".join(cmd))


def multisign_tx(unsigned_tx_path: str, multi_sig_account_name: str, *signed_tx):
    secret_cli_posix = Path(secret_cli).as_posix()
    signed_tx_posix = map(lambda x: Path(x).as_posix(), signed_tx)
    return run_secret_cli(['secretcli', 'tx', 'multisign', unsigned_tx_path, multi_sig_account_name]+
                          list(signed_tx_posix))
    # return run_secret_cli(" ".join([secret_cli_posix, 'tx', 'multisign', unsigned_tx_path, multi_sig_account_name]
    #                                + list(signed_tx_posix)))


def create_unsigined_tx(secret_contract_addr: str, encoded_args: str, multisig_acc_addr: str) -> str:
    secret_cli_posix = Path(secret_cli).as_posix()
    enclave_key_posix = Path(enclave_key).as_posix()

    cmd = ['secretcli', 'tx', 'compute', 'execute', secret_contract_addr, f"'{encoded_args}'",
           '--generate-only', '--chain-id', f"{chain_id}", '--enclave-key', enclave_key_posix, '--code-hash',
           enclave_hash, '--from', multisig_acc_addr]
    return run_secret_cli(cmd)
    # return run_secret_cli(" ".join(cmd))


def broadcast(signed_tx_path: str):
    secret_cli_posix = Path(secret_cli).as_posix()
    signed_tx_path_posix = Path(signed_tx_path).as_posix()
    cmd = ['secretcli', 'tx', 'broadcast', signed_tx_path_posix]
    return run_secret_cli(cmd)
    # return run_secret_cli(" ".join(cmd))


def decrypt(data):
    secret_cli_posix = Path(secret_cli).as_posix()
    cmd = ['secretcli', 'query', 'compute', 'decrypt', data]
    return run_secret_cli(cmd)
    # return run_secret_cli(" ".join(cmd))


def run_secret_cli(cmd: List[str]) -> str:
    # cmd = bash + [cmd]
    p = run(tuple(cmd), stdout=PIPE, stderr=PIPE)

    err = p.stderr
    if err:
        raise RuntimeError(err.decode())

    return p.stdout.decode()
