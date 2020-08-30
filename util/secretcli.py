import subprocess

from config import secret_cli


def sign_tx(unsigned_tx_path: str, multi_sig_account_addr: str, account_name: str, output_file: str):
    cmd = f"{secret_cli} tx sign {unsigned_tx_path}" \
          f" --multisig {multi_sig_account_addr}" \
          f" --from={account_name}" \
          f" --output-document={output_file}"
    return run_secret_cli(cmd)


def multisin_tx(multi_sig_account_name: str, unsiged_tx: str, *signed_tx) -> str:
    signed = " ".join(signed_tx)
    cmd = f"{secret_cli} tx multisign {unsiged_tx} {multi_sig_account_name} {signed}"
    return run_secret_cli(cmd)


def run_secret_cli(cmd) -> str:
    res = subprocess.run(cmd, shell=True, capture_output=True)
    if len(res.stderr) > 0:
        raise RuntimeError(f"Error while using secretcli: {res.stderr.decode()}")

    return res.stdout.decode()


def broadcast(signed_tx: str):
    return run_secret_cli(f"secretcli tx broadcast {signed_tx}")
