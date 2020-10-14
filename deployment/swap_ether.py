import json

from src.contracts.ethereum.message import Message
from src.contracts.ethereum.multisig_wallet import MultisigWallet
from src.util.config import Config
from src.util.web3 import web3_provider, send_contract_tx


def swap_eth():

    cfg = Config()

    private_key = ""  # your private key here
    account = ""  # your account here

    with open('./src/contracts/ethereum/compiled/MultiSigSwapWallet.json', 'r') as f:
        contract_source_code = json.loads(f.read())

    w3 = web3_provider(cfg['eth_node_address'])
    # multisig_wallet = MultisigWallet(web3_provider, config.multisig_wallet_address)
    multisig_wallet = MultisigWallet(w3, cfg['multisig_wallet_address'])

    class SwapMessage(Message):
        def args(self):
            return "secret13l72vhjngmg55ykajxdnlalktwglyqjqv9pkq4".encode(),

    m = SwapMessage()
    tx_hash = send_contract_tx(multisig_wallet.contract, 'swap',
                               account, bytes.fromhex(private_key), *m.args(), value=200)
    print(repr(tx_hash))


if __name__ == '__main__':
    swap_eth()
