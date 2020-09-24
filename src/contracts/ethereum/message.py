from abc import abstractmethod
from typing import Tuple


class Message:
    @abstractmethod
    def args(self) -> Tuple:
        """converts msg attributes into args tuple"""
        pass


class Submit(Message):
    def __init__(self, dest: str, amount: int, nonce: int, data=b""):
        self.dest = dest
        self.amount = amount
        self.nonce = nonce
        self.data = data

    def args(self) -> Tuple:
        return self.dest, self.amount, self.nonce, self.data


class Confirm(Message):
    def __init__(self, submission_id: int):
        self.submission_id = submission_id

    def args(self):
        return self.submission_id,
