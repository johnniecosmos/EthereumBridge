from ecdsa import SigningKey, SECP256k1, VerifyingKey
from ethereum.utils import ecsign

from src.util.web3 import w3

from src.util.crypto_store.crypto_manager import CryptoManagerBase


class LocalCryptoStore(CryptoManagerBase):
    def __init__(self, private_key: bytes = b'', account: str = ''):
        self.private_key = private_key
        self.public_key = b''

        self._address = account

        assert w3.eth.account.from_key(self.private_key).address == self._address

    def generate(self):
        sk = SigningKey.generate(curve=SECP256k1)
        vk: VerifyingKey = sk.verifying_key
        self.public_key = vk.to_string()
        self.private_key = sk.to_string()
        self._address = w3.eth.account.from_key(self.private_key).address

    @property
    def address(self) -> str:
        return self._address

    def sign(self, tx_hash: str):
        msg_bytes = bytes.fromhex(tx_hash)

        v, r, s = ecsign(msg_bytes, self.private_key)

        return r, s, v
