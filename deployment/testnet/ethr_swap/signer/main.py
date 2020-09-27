from mongoengine import connect
from web3 import Web3

from deployment.testnet.ethr_swap.signer import config

from src.contracts.ethereum.multisig_wallet import MultisigWallet
from src.event_listener import EventListener
from src.singer.ehtr_signer import EthrSigner
from src.singer.secret_signer import SecretSigner, MultiSig

web3_provider = Web3(Web3.HTTPProvider(config.provider_address))
multisig_wallet = MultisigWallet(web3_provider, config.multisig_wallet_address)
event_listener = EventListener(multisig_wallet, web3_provider, config)

multi_sig_acc = MultiSig(config.multisig_acc_addr, config.multisig_key_name)
singer_acc = MultiSig(config.multisig_acc_addr, config.signer_key_name)


if __name__ == "__main__":
    connection = connect(db=config.db_name)
    ethr_signer = EthrSigner(event_listener, web3_provider, multisig_wallet,
                             config.signer_key, config.signer_acc_addr, config)
    scrt_signer = SecretSigner(web3_provider, singer_acc, multisig_wallet, config)
    pass  # will program exit? it shouldn't
