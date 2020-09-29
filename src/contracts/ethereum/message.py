from abc import abstractmethod
from typing import Tuple


class Message:
    """Base class for all EthereumContract's messages"""
    @abstractmethod
    def args(self) -> Tuple:
        """converts msg attributes into args tuple"""
        pass

    def __repr__(self):
        return f"{self.__class__.__name__}: Args: {self.args()}"


class Submit(Message):
    """MultisigWallet submitTransaction message"""
    def __init__(self, dest: str, amount: int, nonce: int, data=b""):
        self.dest = dest
        self.amount = amount
        self.nonce = nonce
        self.data = data

    def args(self) -> Tuple:
        return self.dest, self.amount, self.nonce, self.data



class Confirm(Message):
    """MultisigWallet confirmTransaction message"""
    def __init__(self, submission_id: int):
        self.submission_id = submission_id

    def args(self):
        return self.submission_id,
