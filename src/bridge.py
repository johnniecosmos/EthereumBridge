import sys
from threading import Thread
from time import sleep
from typing import List

from src.contracts.ethereum.multisig_wallet import MultisigWallet
from src.db import database
from src.leader.eth.leader import EtherLeader
from src.leader.secret20 import Secret20Leader
from src.signer.eth.signer import EtherSigner
from src.signer.secret20 import Secret20Signer
from src.signer.secret20.signer import SecretAccount
from src.util.common import Token, bytes_from_hex
from src.util.config import Config
from src.util.crypto_store.local_crypto_store import LocalCryptoStore
from src.util.crypto_store.pkcs11_crypto_store import Pkcs11CryptoStore
from src.util.logger import get_logger
from src.util.secretcli import configure_secretcli
from src.util.web3 import w3


def chain_objects(signer, leader) -> dict:
    return {'signer': signer, 'leader': leader}


SUPPORTED_TYPES = ['erc20', 'eth', 's20', 'scrt']

SUPPORTED_COINS = [{'dai': 'sdai'}, {'eth': 'seth'}]

NETWORK_PARAMS = {
    'dai': {'type': 'erc20',
            'mainnet': {'address': '0x06526C574BA6e45069057733bB001520f08b59ff',
                        'decimals': 6},
            'ropsten': {'address': '0x06526C574BA6e45069057733bB001520f08b59ff',
                        'decimals': 6},
            'local': {'address': '0x06526C574BA6e45069057733bB001520f08b59ff',
                      'decimals': 6},
            },
    'sdai': {'type': 's20',
             'mainnet': {'address': 'secret1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
                         'decimals': 6},
             'holodeck': {'address': 'secret1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
                          'decimals': 6}},
    'eth': {'type': 'eth'},
    'seth': {'type': 's20',
             'mainnet': {'address': 'secret1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
                         'decimals': 6},
             'holodeck': {'address': 'secret1hx84ff3h4m8yuvey36g9590pw9mm2p55cwqnm6',
                          'code_hash': '',
                          'decimals': 6}},
}


tracked_tokens_eth = {"native": Token("secret1hx84ff3h4m8yuvey36g9590pw9mm2p55cwqnm6", "secret-eth")}
tracked_tokens_scrt = {"secret1hx84ff3h4m8yuvey36g9590pw9mm2p55cwqnm6": Token("native", "eth")}


def run_bridge():  # pylint: disable=too-many-statements
    runners = []
    logger = get_logger(logger_name='runner')
    required_configs = ['MODE', 'secret_node', 'multisig_acc_addr', 'chain_id']
    cfg = Config(required=required_configs)
    try:
        configure_secretcli(cfg)
    except RuntimeError:
        logger = get_logger(logger_name='runner')
        logger.error('Failed to set up secretcli')
        sys.exit(1)

    if cfg['token']:
        signer = Pkcs11CryptoStore(store=cfg["PKCS11_MODULE"], token=cfg["token"], user_pin=cfg["user_pin"],
                                   label=cfg.get('label'))
    else:
        signer = LocalCryptoStore(private_key=bytes_from_hex(cfg['eth_private_key']), account=cfg['eth_address'])

    logger.info(f'Starting with ETH address {signer.address}')

    with database(db=cfg['db_name'], host=cfg['db_host'],
                  password=cfg['db_password'], username=cfg['db_username']):

        eth_wallet = MultisigWallet(w3, cfg['multisig_wallet_address'])

        secret_account = SecretAccount(cfg['multisig_acc_addr'], cfg['secret_key_name'])

        eth_signer = EtherSigner(eth_wallet, signer, dst_network="Secret", config=cfg)
        s20_signer = Secret20Signer(secret_account, eth_wallet, cfg)

        runners.append(eth_signer)
        runners.append(s20_signer)

        if cfg['MODE'].lower() == 'leader':
            eth_leader = EtherLeader(eth_wallet, signer, dst_network="Secret", config=cfg)

            secret_leader = SecretAccount(cfg['multisig_acc_addr'], cfg['multisig_key_name'])
            s20_leader = Secret20Leader(secret_leader, eth_wallet, src_network="Ethereum", config=cfg)

            runners.append(eth_leader)
            runners.append(s20_leader)

        run_all(runners)


def run_all(runners: List[Thread]):
    for r in runners:
        r.start()

    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for r in runners:
            if r.is_alive():
                r.stop()


if __name__ == '__main__':
    run_bridge()
