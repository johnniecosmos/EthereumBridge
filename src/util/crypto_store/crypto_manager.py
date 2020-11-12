from typing import Tuple


class CryptoManagerBase:
    def generate(self):
        raise NotImplementedError

    @property
    def address(self) -> str:
        raise NotImplementedError

    def sign(self, tx_hash: str) -> Tuple[int, int, int]:
        raise NotImplementedError
