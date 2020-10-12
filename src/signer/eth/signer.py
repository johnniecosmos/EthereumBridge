from threading import Thread, Event
from time import sleep

from src.contracts.ethereum.event_listener import EthEventListener
from src.contracts.ethereum.multisig_wallet import MultisigWallet
from src.signer.eth.historical import HistoricalEthSigner
from src.util.config import Config
from src.util.logger import get_logger


class EtherSigner(Thread):
    """
    secretETH --> Swap TX --> ETH

    On Ethereum the leader monitors the sETH Secret Contract. When it sees a new swap, it will
    broadcast a submit transaction on-chain.
    On detecting a submit transaction from the event listener, the signer signs and broadcasts
    a confirm transaction on-chain. The multisig contract, after receiving a number of confirmations
    greater than the set threshold will trigger the transfer of funds

    Will first attempt to catch up with unsigned transactions by scanning past events,
    and only then will start monitoring new transactions.

    The account set here must have enough ETH for all the transactions you're planning on doing
    """
    def __init__(self, contract: MultisigWallet, private_key: bytes, account: str, config: Config, **kwargs):
        self.account = account
        self.private_key = private_key
        self.event_listener = EthEventListener(contract, config)
        self.stop_event = Event()
        self.logger = get_logger(db_name=config['db_name'],
                                 logger_name=config.get('logger_name', f"{self.__class__.__name__}-{self.account[0:5]}"))
        self.signer = HistoricalEthSigner(contract, self.private_key, self.account, config)

        super().__init__(group=None, name=f"{self.__class__.__name__}-{self.account[0:5]}", target=self.run, **kwargs)

    def run(self):
        self.logger.info("Starting..")
        self.signer.sign_all_historical_swaps()
        # then we can start signing new transactions
        self.event_listener.register(self.signer.handle_submission, ['Submission'])
        self.event_listener.start()
        while not self.stop_event.is_set():
            if not self.event_listener.is_alive():
                self.logger.critical("Event listener stopped - stopping signer")
                self.stop()
            sleep(10)

    def stop(self):
        self.logger.info("Stopping..")
        self.event_listener.stop()
        self.stop_event.set()
