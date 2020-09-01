from subprocess import run, PIPE
from pathlib import Path

from config import secret_cli, enclave_hash, enclave_key, chain_id

bash = [r"C:\Program Files\Git\bin\bash.exe", "-c"]


def sign_tx(unsigned_tx: str, multi_sig_account_addr: str, account_name: str):
    secret_cli_posix = Path(secret_cli).as_posix()
    unsigned_tx_posix = Path(unsigned_tx).as_posix()
    return run_secret_cli(" ".join([secret_cli_posix, 'tx', 'sign', unsigned_tx_posix, '--signature-only', '--multisig',
                                    multi_sig_account_addr, '--from', account_name]))


def multisin_tx(unsigned_tx_path: str, multi_sig_account_name: str, *signed_tx):
    secret_cli_posix = Path(secret_cli).as_posix()
    return run_secret_cli(" ".join([secret_cli, 'tx', 'multisign', unsigned_tx_path, multi_sig_account_name]
                                   + list(secret_cli_posix)))


def create_unsigined_tx(secret_contract_addr: str, encoded_args: str, multisig_acc_addr: str) -> str:
    secret_cli_posix = Path(secret_cli).as_posix()
    enclave_key_posix = Path(enclave_key).as_posix()

    cmd = [secret_cli_posix, 'tx', 'compute', 'execute', secret_contract_addr, encoded_args,
           '--generate-only', '--chain-id', f"{chain_id}", '--enclave-key', enclave_key_posix, '--code-hash',
           enclave_hash, '--from', multisig_acc_addr]
    return run_secret_cli(" ".join(cmd))


def broadcast(signed_tx: str):
    return run_secret_cli(f"secretcli tx broadcast {signed_tx}")


def decrypt(data):
    secret_cli_posix = Path(secret_cli).as_posix()
    cmd = [secret_cli_posix, 'query', 'compute', 'decrypt', data]
    return run_secret_cli(" ".join(cmd))


def run_secret_cli(cmd: str) -> str:
    # TODO: test it with subprocess.check_call
    cmd = bash + [cmd]
    p = run(cmd, stdout=PIPE, stderr=PIPE)
    res, err = p.stdout, p.stderr
    if err:
        raise RuntimeError(err.decode())
    return res.decode()
