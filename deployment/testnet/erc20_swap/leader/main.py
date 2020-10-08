from mongoengine import connect
from web3 import Web3

from deployment.testnet.erc20_swap.leader import config
from src.contracts.ethereum.erc20 import Erc20
from src.contracts.ethereum.message import Message
from src.contracts.ethereum.multisig_wallet import MultisigWallet
from src.contracts.ethereum.event_listener import EthEventListener
from src.leader.eth.leader import EtherLeader
from src.leader.secret20.leader import SecretLeader
from src.leader.secret20.manager import SecretManager
from src.signer.secret20.signer import MultiSig

web3_provider = Web3(Web3.HTTPProvider(config.provider_address))
multisig_wallet = MultisigWallet(web3_provider, config.multisig_wallet_address)
erc20_contract = Erc20(web3_provider, config.token_contract_addr, multisig_wallet.address)
# here we tell event_listener to track the erc20_contract
event_listener = EthEventListener(erc20_contract, web3_provider, config)

multi_sig_acc = MultiSig(config.multisig_acc_addr, config.multisig_key_name)


class Transfer(Message):
    def args(self):
        return Web3.toChecksumAddress("0xef06222f18a008cd3635a8325208fc0ff934d830"), 7, "secret1sf7zjlg7u6uw0hyypy3akw3qtryt3p4e2gknxa".encode(), # this is signer 1 address


if __name__ == "__main__":
    connection = connect(db=config.db_name)
    ethr_leader = EtherLeader(web3_provider, multisig_wallet, config)
    scrt_leader = SecretLeader(multi_sig_acc, config)
    # Notice that here, we track erc20_contract
    manager = SecretManager(event_listener, erc20_contract, multi_sig_acc, config)
    m = Transfer()
    # tx_hash = send_contract_tx(ethr_leader.provider, ethr_leader.token_contract.contract, 'transfer',
    #                            ethr_leader.default_account, ethr_leader.private_key, *m.args())
    # print(tx_hash.hex())
