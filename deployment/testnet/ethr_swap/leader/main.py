from mongoengine import connect
from web3 import Web3

from deployment.testnet.ethr_swap.leader import config
from src.contracts.ethereum.message import Message
from src.contracts.ethereum.multisig_wallet import MultisigWallet
from src.event_listener import EventListener
from src.leader.ethr_leader import EthrLeader
from src.leader.secret_leader import SecretLeader
from src.manager import Manager
from src.singer.secret_signer import MultiSig


class SwapMessage(Message):
    def args(self):
        return config.multisig_acc_addr.encode(),


web3_provider = Web3(Web3.HTTPProvider(config.provider_address))
multisig_wallet = MultisigWallet(web3_provider, config.multisig_wallet_address)
event_listener = EventListener(multisig_wallet, web3_provider, config)

multi_sig_acc = MultiSig(config.multisig_acc_addr, config.multisig_key_name)

if __name__ == "__main__":
    connection = connect(db=config.db_name)
    ethr_leader = EthrLeader(web3_provider, multisig_wallet, config.leader_key, config.leader_acc_addr, config)
    scrt_leader = SecretLeader(multi_sig_acc, config)
    manager = Manager(event_listener, multisig_wallet, multi_sig_acc, config)
    pass
