from web3 import Web3

from deployment.testnet import config
from src.contracts.ethereum.multisig_wallet import MultisigWallet
from src.event_listener import EventListener
from src.leader.ethr_leader import EthrLeader
from src.leader.secret_leader import SecretLeader
from src.singer.ehtr_signer import EthrSigner
from src.singer.secret_signer import SecretSigner, MultiSig
from src.manager import Manager

web3_provider = Web3(Web3.HTTPProvider(config.provider_address))
multisig_wallet = MultisigWallet(web3_provider, config.multisig_wallet_address)
event_listener = EventListener(multisig_wallet, web3_provider, config)

multi_sig_acc = MultiSig(config.multisig_acc_addr, config.multisig_key_name)
singer_acc = MultiSig(config.multisig_acc_addr, config.signer_key_name)

ethr_leader = EthrLeader(web3_provider, multisig_wallet, config.ethr_private_key, config.acc_addr, config)
scrt_leader = SecretLeader(multi_sig_acc, config)
ehtr_signer = EthrSigner(event_listener, web3_provider, multisig_wallet,
                         config.ethr_private_key, config.acc_addr, config)
scrt_signer = SecretSigner(web3_provider, singer_acc, multisig_wallet, config)
manager = Manager(event_listener, multisig_wallet, multi_sig_acc, config)

if __name__ == "__main__":
    pass
