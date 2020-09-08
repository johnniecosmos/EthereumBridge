from time import sleep

from web3 import Web3

from src.db.collections.eth_swap import ETHSwap, Status
from src.db.collections.signatures import Signatures


def test_0(swap_contract, owners):
    # validate owners of contract - sanity check
    contract_owners = swap_contract.getOwners()
    assert len(contract_owners) == len(owners)
    for owner in owners:
        assert owner in contract_owners


def test_1(manager, signers, web3_provider, test_configuration, contract):
    tx_hash = contract.contract.functions.swap(signers[0].multisig.multisig_acc_addr.encode()). \
        transact({'from': web3_provider.eth.coinbase, 'value': 7}).hex().lower()
    # chain is initiated with block number one, and the contract tx will be block # 2
    assert increase_block_number(web3_provider, test_configuration.blocks_confirmation_required - 1)

    sleep(test_configuration.default_sleep_time_interval)

    assert ETHSwap.objects(tx_hash=tx_hash).count() == 0  # verify blocks confirmation threshold wasn't meet
    assert increase_block_number(web3_provider, 1)  # add the 'missing' confirmation block

    # give event listener and manager time to process tx
    sleep(test_configuration.default_sleep_time_interval)
    assert ETHSwap.objects(tx_hash=tx_hash).count() == 1  # verify swap event recorded

    # check signers were notified of the tx and signed it
    assert Signatures.objects().count() == len(signers)

    # give time for manager to process the signatures
    sleep(test_configuration.manager_sleep_time_seconds)
    assert ETHSwap.objects().get().status == Status.SWAP_STATUS_SIGNED.value


def test_2(leader, test_configuration):
    # give leader time to multisign already existing signatures
    sleep(1)
    assert ETHSwap.objects().get().status == Status.SWAP_STATUS_SUBMITTED.value


def increase_block_number(web3_provider: Web3, increment: int) -> True:
    # Creates stupid tx on the chain to increase the last block number
    for i in range(increment):
        web3_provider.eth.sendTransaction({
            'from': web3_provider.eth.coinbase,
            'to': web3_provider.eth.accounts[1],
            'value': 100
        })
    return True
