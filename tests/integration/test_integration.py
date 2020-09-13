from time import sleep

from pytest import fixture
from web3 import Web3

from src.db.collections.eth_swap import ETHSwap, Status
from src.db.collections.signatures import Signatures
from src.util.web3 import normalize_address


# Note: The tests are ordered and named test_0...N and should be executed in that order as they demonstrate the flow
# Ethr -> Scrt and then Scrt -> Ethr


def test_0(swap_contract, ethr_signers):
    # validate owners of contract - sanity check
    contract_owners = swap_contract.getOwners()
    assert len(contract_owners) == len(ethr_signers)
    for owner in ethr_signers:
        assert owner.default_account in contract_owners


# TL;DR: Covers from swap tx to multisig in db(tx ready to be sent to scrt)
# Components tested:
# 1. Event listener registration recognize contract events
# 2. Manager status update and multisig creation.
# 3. SecretSigners validation and signing.
# 4. Smart Contract swap functionality.
def test_1(manager, scrt_signers, web3_provider, test_configuration, contract):
    tx_hash = contract.contract.functions.swap(scrt_signers[0].multisig.multisig_acc_addr.encode()). \
        transact({'from': web3_provider.eth.coinbase, 'value': 100}).hex().lower()
    # TODO: validate money increase of the smart contract
    # chain is initiated with block number one, and the contract tx will be block # 2
    assert increase_block_number(web3_provider, test_configuration.blocks_confirmation_required - 1)

    sleep(test_configuration.default_sleep_time_interval)

    assert ETHSwap.objects(tx_hash=tx_hash).count() == 0  # verify blocks confirmation threshold wasn't meet
    assert increase_block_number(web3_provider, 1)  # add the 'missing' confirmation block

    # give event listener and manager time to process tx
    sleep(test_configuration.default_sleep_time_interval)
    assert ETHSwap.objects(tx_hash=tx_hash).count() == 1  # verify swap event recorded

    # check signers were notified of the tx and signed it
    assert Signatures.objects().count() == len(scrt_signers)

    # give time for manager to process the signatures
    sleep(test_configuration.manager_sleep_time_seconds)
    assert ETHSwap.objects().get().status == Status.SWAP_STATUS_SIGNED.value


# TL;DR: Covers from Leader broadcast of signed tx, (TODO): creation of burn events in secret and leader recognition of it
# Components tested:
# 1. Leader broadcast to scrt.
# 2. Secret Contract "mint" and "burn"
# 3. Leader "burn" event tracking
def test_2(leader, test_configuration, contract, web3_provider, scrt_signers):
    # give leader time to multi-sign already existing signatures
    sleep(1)
    assert ETHSwap.objects().get().status == Status.SWAP_STATUS_SUBMITTED.value

    # Create a "burn" tx on SCRT
    pass  # TODO
    # Verify that leader recognized the burn tx (might not be possible)

    # Verify that leader send tx to the smart contract


@fixture(scope="module")
def test_3_setup(web3_provider, contract, leader, ethr_signers):
    del ethr_signers[-1]  # delete one of the singers so threshold won't be reached
    # create data to be used
    mock_submit_tx(web3_provider, contract, leader)

    # send some useless data - number is arbitrary
    increase_block_number(web3_provider, 3)


# TL;DR: EthrSigner event response and multisig logic
# Components tested:
# 1. EthrSigner - confirmation and offline catchup
# 2. SmartContract multisig functionality
def test_3(test_3_setup, contract, web3_provider, ethr_signers, ethr_signer_late, leader, test_configuration):
    # use ethr_signer_late to test the catch up (the submit tx won't work without it)
    # validate with contract

    # create mock submit transaction - this should be caught by the event listener TODO: Remove
    mock_submit_tx(web3_provider, contract, leader)
    # validate it
    sleep(test_configuration.default_sleep_time_interval)
    executed_index = 3
    assert contract.contract.functions.transactions(0).call()[executed_index]


# TODO: Remove
def mock_submit_tx(web3_provider, contract, leader):
    withdraw_dest = normalize_address(web3_provider.eth.accounts[-1])
    withdraw_value = 20
    submit_tx = contract.contract.functions.submitTransaction(withdraw_dest, withdraw_value, "scrt tx hash".encode()). \
        buildTransaction(
        {
            'from': leader.default_account,
            'chainId': web3_provider.eth.chainId,
            'gasPrice': web3_provider.eth.gasPrice,
            'nonce': web3_provider.eth.getTransactionCount(leader.default_account),
        })
    signed_txn = web3_provider.eth.account.sign_transaction(submit_tx, private_key=leader.private_key)
    web3_provider.eth.sendRawTransaction(signed_txn.rawTransaction)


def increase_block_number(web3_provider: Web3, increment: int) -> True:
    # Creates stupid tx on the chain to increase the last block number
    for i in range(increment):
        web3_provider.eth.sendTransaction({
            'from': web3_provider.eth.coinbase,
            'to': web3_provider.eth.accounts[1],
            'value': 100
        })
    return True
