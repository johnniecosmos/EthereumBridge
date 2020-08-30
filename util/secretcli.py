import subprocess

from config import secret_cli


def sign_tx(unsigned_tx_path: str, multi_sig_account_addr: str, account_name: str, output_file: str):
    cmd = f"{secret_cli} tx sign {unsigned_tx_path}" \
          f" --multisig {multi_sig_account_addr}" \
          f" --from={account_name}" \
          f" --output-document={output_file}"
    return run_secret_cli(cmd)


def multisin_tx(unsigned_tx_path: str, multi_sig_account_name: str, *args):
    signed = " ".join(args)
    cmd = f"{secret_cli} tx multisign {unsigned_tx_path} {multi_sig_account_name} {signed} > signed.json"
    return run_secret_cli(cmd)


def run_secret_cli(cmd) -> str:
    # TODO: test it with subprocess.check_call
    res = subprocess.run(cmd, shell=True, capture_output=True)
    if len(res.stderr) > 0:
        raise RuntimeError(f"Error while using secretcli: {res.stderr.decode()}")

    return res.stdout.decode()
