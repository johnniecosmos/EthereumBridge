from mongoengine import connect
from web3 import Web3

from deployment.testnet.ethr_swap.leader import config
from src.contracts.ethereum.message import Message
from src.contracts.ethereum.multisig_wallet import MultisigWallet
from src.contracts.ethereum.event_listener import EthEventListener
from src.leader.eth.leader import EtherLeader
from src.leader.secret20.leader import SecretLeader
from src.leader.secret20.manager import SecretManager
from src.signer.secret20.signer import MultiSig


class SwapMessage(Message):
    def args(self):
        return config.multisig_acc_addr.encode(),


web3_provider = Web3(Web3.HTTPProvider(config.provider_address))
multisig_wallet = MultisigWallet(web3_provider, config.multisig_wallet_address)
event_listener = EthEventListener(multisig_wallet, web3_provider, config)

multi_sig_acc = MultiSig(config.multisig_acc_addr, config.multisig_key_name)

if __name__ == "__main__":
    connection = connect(db=config.db_name)
    ethr_leader = EtherLeader(web3_provider, multisig_wallet, config)
    scrt_leader = SecretLeader(multi_sig_acc, config)
    manager = SecretManager(event_listener, multisig_wallet, multi_sig_acc, config)
    pass
