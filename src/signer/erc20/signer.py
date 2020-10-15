from src.contracts.ethereum.erc20 import Erc20
from src.contracts.ethereum.event_listener import EthEventListener
from src.contracts.ethereum.multisig_wallet import MultisigWallet
from src.signer.erc20.impl import _ERC20SignerImpl
from src.signer.eth.signer import EtherSigner
from src.util.common import Token
from src.util.config import Config
from src.util.web3 import web3_provider


class ERC20Signer(EtherSigner):
    """
    secretERC20 --> Swap TX --> ERC20

    See EtherSigner for a description of what this does - just replace ETH with ERC20 :)

    """
    def __init__(self, contract: MultisigWallet, token: Token, private_key: bytes, account: str, config: Config,
                 **kwargs):
        super().__init__(contract, private_key, account, config, **kwargs)

        # everything is basically the same, just overload the signer and event listener
        token_contract = Erc20(web3_provider(config['eth_node_address']),
                               token,
                               contract.address)
        self.signer = _ERC20SignerImpl(contract, token, private_key, account, config)
        self.event_listener = EthEventListener(token_contract, config)
