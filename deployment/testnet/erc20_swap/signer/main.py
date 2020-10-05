from mongoengine import connect
from web3 import Web3

from deployment.testnet.erc20_swap.signer import config
from src.contracts.ethereum.erc20 import Erc20
from src.contracts.ethereum.multisig_wallet import MultisigWallet
from src.contracts.ethereum.event_listener import EventListener
from src.signer.ether_signer import EtherSigner
from src.signer.secret_signer import SecretSigner, MultiSig

web3_provider = Web3(Web3.HTTPProvider(config.provider_address))
multisig_wallet = MultisigWallet(web3_provider, config.multisig_wallet_address)
erc20_contract = Erc20(web3_provider, config.token_contract_addr, multisig_wallet.address)
event_listener = EventListener(multisig_wallet, web3_provider, config)

multi_sig_acc = MultiSig(config.multisig_acc_addr, config.multisig_key_name)
singer_acc_1 = MultiSig(config.multisig_acc_addr, config.signer_key_name_1)
singer_acc_2 = MultiSig(config.multisig_acc_addr, config.signer_key_name_2)

if __name__ == "__main__":
    connection = connect(db=config.db_name)
    # signer 1 is ethr leader
    ethr_signer_2 = EtherSigner(event_listener, multisig_wallet,
                                config.signer_key_2, config.signer_acc_addr_2, config)
    ethr_signer_3 = EtherSigner(event_listener, multisig_wallet,
                                config.signer_key_3, config.signer_acc_addr_3, config)

    scrt_signer_1 = SecretSigner(web3_provider, singer_acc_1, erc20_contract, config)
    scrt_signer_2 = SecretSigner(web3_provider, singer_acc_2, erc20_contract, config)
