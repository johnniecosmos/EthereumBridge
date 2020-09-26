import json
from decimal import Decimal
from pathlib import Path
from subprocess import run, PIPE
from time import sleep

from web3 import Web3

from src.db.collections.eth_swap import ETHSwap, Status
from src.db.collections.management import Source, Management
from src.db.collections.signatures import Signatures
from src.singer.ehtr_signer import EthrSigner
from src.util.common import project_base_path
from src.util.web3 import event_log
# Note: The tests are ordered and named test_0...N and should be executed in that order as they demonstrate the flow
# Ethr -> Scrt and then Scrt -> Ethr
from tests.utils.keys import get_key_signer

TRANSFER_AMOUNT = 100


def test_0(setup):
    pass


# TL;DR: Covers from swap tx to multisig in db(tx ready to be sent to scrt)
# Components tested:
# 1. Event listener registration recognize contract events
# 2. Manager status update and multisig creation.
# 3. SecretSigners validation and signing.
# 4. Smart Contract swap functionality.
def test_1(manager, scrt_signers, web3_provider, configuration, erc20_contract, multisig_wallet):
    t1_address = get_key_signer("t1", Path.joinpath(project_base_path(), 'tests', 'keys'))['address']
    # swap ethr for scrt token, deliver tokens to address of 'a'(we will use 'a' later to check it received the money)
    tx_hash = erc20_contract.contract.functions.transfer(multisig_wallet.address,
                                                         TRANSFER_AMOUNT,
                                                         t1_address.encode()).\
        transact({'from': web3_provider.eth.coinbase}).hex().lower()
    assert TRANSFER_AMOUNT == erc20_contract.contract.functions.balanceOf(multisig_wallet.address).call()

    # increase number of blocks to reach the confirmation threshold
    assert increase_block_number(web3_provider, configuration.blocks_confirmation_required - 1)

    sleep(configuration.default_sleep_time_interval + 2)

    assert ETHSwap.objects(tx_hash=tx_hash).count() == 0  # verify blocks confirmation threshold wasn't meet
    assert increase_block_number(web3_provider, 1)  # add the 'missing' confirmation block

    # give event listener and manager time to process tx
    sleep(configuration.default_sleep_time_interval + 2)
    assert ETHSwap.objects(tx_hash=tx_hash).count() == 1  # verify swap event recorded

    sleep(1)
    # check signers were notified of the tx and signed it
    assert Signatures.objects().count() == len(scrt_signers)

    # give time for manager to process the signatures
    sleep(configuration.default_sleep_time_interval + 2)
    assert ETHSwap.objects().get().status == Status.SWAP_STATUS_SIGNED.value


# Covers from Leader broadcast of signed tx to scrt swap tx submission on smart contract (withdraw)
# Components tested:
# 1. Leader broadcast to scrt multi-signed mint
# 2. Secret Contract "mint"
def test_2(scrt_leader, configuration, erc20_contract, web3_provider, scrt_signers):
    # give scrt_leader time to multi-sign already existing signatures
    sleep(configuration.default_sleep_time_interval + 3)
    assert ETHSwap.objects().get().status == Status.SWAP_STATUS_SUBMITTED.value

    # get tx details
    tx_hash = ETHSwap.objects().get().tx_hash
    _, log = event_log(tx_hash, ['Transfer'], web3_provider, erc20_contract.contract)
    transfer_amount = web3_provider.fromWei(erc20_contract.extract_amount(log), 'ether')
    dest = erc20_contract.extract_addr(log)

    # validate swap tx on ethr delivers to the destination
    balance_query = '{"balance": {}}'
    tx_hash = run(f"secretcli tx compute execute {configuration.secret_contract_address} "
                  f"'{balance_query}' --from {dest} -b block -y | jq '.txhash'", shell=True, stdout=PIPE)
    tx_hash = tx_hash.stdout.decode().strip()[1:-1]

    res = run(f"secretcli q compute tx {tx_hash} | jq '.output_log' | jq '.[0].attributes' "
              f"| jq '.[3].value'", shell=True, stdout=PIPE).stdout.decode().strip()[1:-1]
    end_index = res.find(' ')
    amount = Decimal(res[:end_index])

    assert abs(transfer_amount - amount) < 1  # TODO: == 0 after specificity fixed


# covers EthrLeader tracking of swap events in scrt and creating submission event in Ethereum
# ethr_signers are here to respond for leader's submission
def test_3(ethr_leader, configuration, ethr_signers):
    # Generate swap tx on secret network
    swap = {"swap": {"amount": str(TRANSFER_AMOUNT), "network": "Ethereum", "destination": ethr_leader.default_account}}
    last_nonce = Management.last_processed(Source.scrt.value, ethr_leader.logger)
    tx_hash = run(f"secretcli tx compute execute {configuration.secret_contract_address} "
                  f"'{json.dumps(swap)}' --from t1 -y", shell=True, stdout=PIPE, stderr=PIPE)
    tx_hash = json.loads(tx_hash.stdout)['txhash']
    # TODO: verify tx_hash

    # Verify that leader recognized the burn tx
    sleep(configuration.default_sleep_time_interval + 6)

    assert last_nonce + 1 == Management.last_processed(Source.scrt.value, ethr_leader.logger)

    # Give ethr signers time to handle the scrt swap tx (will be verified in test_4
    sleep(configuration.default_sleep_time_interval + 1)


# EthrSigner event response and multisig logic
# Components tested:
# 1. EthrSigner - confirmation and offline catchup
# 2. SmartContract multisig functionality
def test_4(event_listener, multisig_wallet, web3_provider, ether_accounts, configuration, ethr_leader):
    # To allow the new EthrSigner to "catch up", we start it after the event submission event in Ethereum
    key = ether_accounts[-1].privateKey
    address = ether_accounts[-1].address
    eth_signer = EthrSigner(event_listener, web3_provider, multisig_wallet, key, address, configuration)

    sleep(configuration.default_sleep_time_interval)
    # Validate the tx is confirmed in the smart contract
    last_nonce = Management.last_processed(Source.scrt.value, eth_signer.logger)
    assert eth_signer.multisig_wallet.contract.functions.confirmations(last_nonce, eth_signer.default_account).call()


def increase_block_number(web3_provider: Web3, increment: int) -> True:
    # Creates arbitrary tx on the chain to increase the last block number
    for i in range(increment):
        web3_provider.eth.sendTransaction({
            'from': web3_provider.eth.coinbase,
            'to': web3_provider.eth.accounts[1],
            'value': 100
        })
    return True
