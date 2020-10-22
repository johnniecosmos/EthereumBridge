import base64
import json
from decimal import Decimal
from pathlib import Path
from subprocess import run, PIPE
from time import sleep

from web3 import Web3

from src.db.collections.eth_swap import Swap, Status
from src.db.collections.swaptrackerobject import SwapTrackerObject
from src.db.collections.signatures import Signatures

from src.util.common import project_base_path
from src.util.config import Config
from src.util.web3 import event_log
# Note: The tests are ordered and named test_0...N and should be executed in that order as they demonstrate the flow
# Ethr -> Scrt and then Scrt -> Ethr
from tests.utils.keys import get_key_signer

TRANSFER_AMOUNT = 100


# Try to swap a token without the token being whitelisted -- should fail
def test_fail_swap_token_not_whitelisted(setup, scrt_leader, scrt_signers, web3_provider, configuration: Config,
                                         erc20_contract, multisig_wallet):

    t1_address = get_key_signer("t1", Path.joinpath(project_base_path(), configuration['path_to_keys']))['address']

    tx_hash = erc20_contract.contract.functions.approve(multisig_wallet.address,
                                                         TRANSFER_AMOUNT). \
        transact({'from': web3_provider.eth.coinbase}).hex().lower()

    try:
        tx_hash = multisig_wallet.contract.functions.swapToken(t1_address.encode(),
                                                               TRANSFER_AMOUNT,
                                                           erc20_contract.address). \
                transact({'from': web3_provider.eth.coinbase}).hex().lower()
    except ValueError:
        pass
    # assert


# TL;DR: Covers from swap tx to multisig in db(tx ready to be sent to secret20)
# Components tested:
# 1. Event listener registration recognize contract events
# 2. Manager status update and multisig creation.
# 3. SecretSigners validation and signing.
# 4. Smart Contract swap functionality.
def test_1_swap_erc_to_s20(scrt_leader, scrt_signers, web3_provider, configuration: Config,
                           erc20_contract, multisig_wallet, ethr_leader):

    secret_token_addr = configuration["sn_token_contracts"]['erc']

    scrt_leader.start()
    for signer in scrt_signers:
        signer.start()

    t1_address = get_key_signer("t1", Path.joinpath(project_base_path(), configuration['path_to_keys']))['address']
    # swap ethr for secret20 token, deliver tokens to address of 'a'.
    # (we will use 'a' later to check it received the money)

    # add usdt to the whitelisted token list
    account = web3_provider.eth.account.from_key(ethr_leader.private_key)

    nonce = web3_provider.eth.getTransactionCount(account.address, "pending")
    tx = multisig_wallet.contract.functions.addToken(erc20_contract.address)
    raw_tx = tx.buildTransaction(transaction={'from': account.address, 'gas': 3000000, 'nonce': nonce})
    signed_tx = account.sign_transaction(raw_tx)
    tx_hash = web3_provider.eth.sendRawTransaction(signed_tx.rawTransaction)

    # Get transaction hash from deployed contract
    tx_receipt = web3_provider.eth.waitForTransactionReceipt(tx_hash)

    # this will likely fail since the test before also allocates the allowance - just ignore if it fails
    try:
        _ = erc20_contract.contract.functions.approve(multisig_wallet.address, TRANSFER_AMOUNT). \
            transact({'from': web3_provider.eth.coinbase})
    except ValueError:
        pass

    tx_hash = multisig_wallet.contract.functions.swapToken(t1_address.encode(),
                                                           TRANSFER_AMOUNT,
                                                           erc20_contract.address). \
        transact({'from': web3_provider.eth.coinbase}).hex().lower()
    assert TRANSFER_AMOUNT == erc20_contract.contract.functions.balanceOf(multisig_wallet.address).call()

    # increase number of blocks to reach the confirmation threshold
    assert increase_block_number(web3_provider, configuration['eth_confirmations'] - 1)

    sleep(configuration['sleep_interval'] + 2)

    assert Swap.objects(src_tx_hash=tx_hash).count() == 0  # verify blocks confirmation threshold wasn't meet
    assert increase_block_number(web3_provider, 1)  # add the 'missing' confirmation block

    # give event listener and manager time to process tx
    sleep(configuration['sleep_interval'] + 2)
    assert Swap.objects(src_tx_hash=tx_hash).count() == 1  # verify swap event recorded

    sleep(1)
    # check signers were notified of the tx and signed it
    assert Signatures.objects().count() == len(scrt_signers)

    # give time for manager to process the signatures
    sleep(configuration['sleep_interval'] + 2)
    assert Swap.objects().get().status == Status.SWAP_SUBMITTED

    # get tx details
    tx_hash = Swap.objects().get().src_tx_hash
    _, log = event_log(tx_hash, ['SwapToken'], web3_provider, multisig_wallet.contract)
    transfer_amount = multisig_wallet.extract_amount(log)
    dest = multisig_wallet.extract_addr(log)

    # validate swap tx on ethr delivers to the destination
    viewing_key_set = '{"set_viewing_key": {"key": "lol"}}'
    tx_hash = run(f"secretcli tx compute execute {secret_token_addr} "
                  f"'{viewing_key_set}' --from {dest} -b block -y | jq '.txhash'", shell=True, stdout=PIPE)
    sleep(6)

    balance = f'{{"balance": {{"key": "lol", "address": "{dest}"}} }}'
    res = run(f"secretcli q compute query {secret_token_addr} "
              f"'{balance}'", shell=True, stdout=PIPE)

    print(f"{res.stdout=}")

    amount = json.loads(res.stdout)["balance"]["amount"]

    print(f"swap amount: {transfer_amount}, dest balance amount: {amount}")

    # give scrt_leader time to multi-sign already existing signatures
    sleep(configuration['sleep_interval'] + 5)
    assert Swap.objects().get().status == Status.SWAP_CONFIRMED


# covers EthrLeader tracking of swap events in secret20 and creating submission event in Ethereum
# ethr_signers are here to respond for leader's submission
def test_2_swap_s20_to_erc(ethr_leader, configuration: Config, ethr_signers, erc20_contract):

    swap_contract_addr = list(configuration['token_map_scrt'].keys())[0]
    secret_token_addr = configuration["sn_token_contracts"]['erc']

    for signer in ethr_signers[:-1]:
        signer.start()

    # Generate swap tx on secret network
    swap = {"send": {"amount": str(TRANSFER_AMOUNT),
                     "msg": base64.b64encode(ethr_leader.default_account.encode()).decode(),
                     "recipient": swap_contract_addr}}

    last_nonce = SwapTrackerObject.last_processed(src=swap_contract_addr)
    tx_hash = run(f"secretcli tx compute execute {secret_token_addr} "
                  f"'{json.dumps(swap)}' --from t1 -b block -y --gas 300000", shell=True, stdout=PIPE, stderr=PIPE)
    tx_hash = json.loads(tx_hash.stdout)['txhash']
    print(f'{tx_hash=}')
    # Verify that leader recognized the burn tx
    sleep(configuration['sleep_interval'] + 6)

    assert last_nonce + 1 == SwapTrackerObject.last_processed(src=swap_contract_addr)


# EthrSigner event response and multisig logic
# Components tested:
# 1. EthrSigner - confirmation and offline catchup
# 2. SmartContract multisig functionality
def test_3_confirm_tx(web3_provider, ethr_signers, configuration: Config, erc20_contract, ethr_leader):

    swap_contract_addr = list(configuration['token_map_scrt'].keys())[0]

    assert increase_block_number(web3_provider, configuration['eth_confirmations'])
    # To allow the new EthrSigner to "catch up", we start it after the event submission event in Ethereum
    ethr_signers[-1].start()

    sleep(configuration['sleep_interval'] + 3)
    # Validate the tx is confirmed in the smart contract
    last_nonce = SwapTrackerObject.last_processed(src=swap_contract_addr)
    assert last_nonce > -1
    assert TRANSFER_AMOUNT == erc20_contract.contract.functions.balanceOf(ethr_leader.default_account).call()


def increase_block_number(web3_provider: Web3, increment: int) -> True:
    # Creates arbitrary tx on the chain to increase the last block number
    for i in range(increment):
        web3_provider.eth.sendTransaction({
            'from': web3_provider.eth.coinbase,
            'to': web3_provider.eth.accounts[1],
            'value': 100
        })
    return True
