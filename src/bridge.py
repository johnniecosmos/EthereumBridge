from os import _exit
from threading import Thread
from time import sleep
from typing import Union, List

from src.contracts.ethereum.erc20 import Erc20
from src.contracts.ethereum.multisig_wallet import MultisigWallet
from src.db import database
from src.leader.erc20.leader import ERC20Leader
from src.leader.eth.leader import EtherLeader
from src.leader.secret20 import Secret20Leader
from src.signer.erc20.signer import ERC20Signer
from src.signer.eth.signer import EtherSigner
from src.signer.secret20 import Secret20Signer
from src.signer.secret20.signer import SecretAccount
from src.util.common import Token, bytes_from_hex
from src.util.config import Config
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


#
#
# chains = {
#     'dai': chain_objects(ERC20Signer, ERC20Leader),
#     'eth': chain_objects(EtherSigner, EtherLeader),
#     'sdai': chain_objects(Secret20Signer, Secret20Leader),
#     'seth': chain_objects(Secret20Signer, Secret20Leader)
# }


def get_token(token_name: str, network: str):
    return Token(NETWORK_PARAMS[token_name][network]['address'], token_name)


def get_leader(coin_name: str, eth_contract: Union[Erc20, MultisigWallet], private_key, account, cfg: Config) -> Thread:
    if NETWORK_PARAMS[coin_name]['type'] == 'erc20':
        token = get_token(coin_name, cfg['network'])
        return ERC20Leader(eth_contract, token, private_key, account, config=cfg)

    if NETWORK_PARAMS[coin_name]['type'] == 'eth':
        return EtherLeader(eth_contract, private_key, account, config=cfg)

    if NETWORK_PARAMS[coin_name]['type'] == 's20':
        s20token = get_token(coin_name, cfg['chain_id'])
        account = SecretAccount(cfg['multisig_acc_addr'], cfg['multisig_key_name'])
        return Secret20Leader(account, s20token, eth_contract, config=cfg)

    raise TypeError


def run_bridge():  # pylint: disable=too-many-statements
    runners = []
    required_configs = ['SRC_COIN', 'DST_COIN', 'MODE', 'private_key', 'account', 'secret_node', 'multisig_acc_addr',
                        'chain_id']
    cfg = Config(required=required_configs)
    try:
        configure_secretcli(cfg)
    except RuntimeError:
        logger = get_logger(logger_name='runner')
        logger.error('Failed to set up secretcli')
        _exit(1)

    with database(db=cfg['db_name'], host=cfg['db_host'],
                  password=cfg['db_password'], username=cfg['db_username']):

        eth_wallet = MultisigWallet(w3, cfg['multisig_wallet_address'])

        private_key = bytes_from_hex(cfg['private_key'])
        account = cfg['account']

        erc20_contract = ''
        secret_account = SecretAccount(cfg['multisig_acc_addr'], cfg['secret_key_name'])

        if NETWORK_PARAMS[cfg['SRC_COIN']]['type'] == 'erc20':
            token = get_token(cfg['SRC_COIN'], cfg['network'])
            erc20_contract = Erc20(w3, token, eth_wallet.address)
            src_signer = ERC20Signer(eth_wallet, token, private_key, account, cfg)
            dst_signer = Secret20Signer(erc20_contract, secret_account, cfg)
        else:
            src_signer = EtherSigner(eth_wallet, private_key, account, cfg)
            dst_signer = Secret20Signer(eth_wallet, secret_account, cfg)

        runners.append(src_signer)
        runners.append(dst_signer)

        if cfg['MODE'].lower() == 'leader':
            src_leader = get_leader(cfg['SRC_COIN'], eth_wallet, private_key, account, cfg)
            if erc20_contract:
                dst_leader = get_leader(cfg['DST_COIN'], erc20_contract, private_key, account, cfg)
            else:
                dst_leader = get_leader(cfg['DST_COIN'], eth_wallet, private_key, account, cfg)
            runners.append(src_leader)
            runners.append(dst_leader)

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
