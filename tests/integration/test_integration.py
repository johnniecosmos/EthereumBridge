import json
from decimal import Decimal
from subprocess import run, PIPE
from time import sleep

from web3 import Web3

from src.db.collections.eth_swap import ETHSwap, Status
from src.db.collections.management import Source, Management
from src.db.collections.signatures import Signatures
from src.signers import EthrSigner
from src.util.web3 import event_log

# Note: The tests are ordered and named test_0...N and should be executed in that order as they demonstrate the flow
# Ethr -> Scrt and then Scrt -> Ethr

TRANSFER_AMOUNT = 100


def test_0(swap_contract, ethr_signers, test_configuration):
    # validate owners of contract - sanity check
    contract_owners = swap_contract.getOwners()
    assert len(contract_owners) == len(ethr_signers) + 1
    for owner in ethr_signers:
        assert owner.default_account in contract_owners


# TL;DR: Covers from swap tx to multisig in db(tx ready to be sent to scrt)
# Components tested:
# 1. Event listener registration recognize contract events
# 2. Manager status update and multisig creation.
# 3. SecretSigners validation and signing.
# 4. Smart Contract swap functionality.
def test_1(manager, scrt_signers, web3_provider, test_configuration, contract):
    # swap ethr for scrt token, deliver tokens to address of 'a'(we will use 'a' later to check it received the money)
    tx_hash = contract.contract.functions.swap(test_configuration.a_address). \
        transact({'from': web3_provider.eth.coinbase, 'value': TRANSFER_AMOUNT}).hex().lower()
    # TODO: validate ethr increase of the smart contract
    # add confirmation threshold -1 new tx after the above swap tx
    assert increase_block_number(web3_provider, test_configuration.blocks_confirmation_required - 1)

    sleep(test_configuration.default_sleep_time_interval + 2)

    assert ETHSwap.objects(tx_hash=tx_hash).count() == 0  # verify blocks confirmation threshold wasn't meet
    assert increase_block_number(web3_provider, 1)  # add the 'missing' confirmation block

    # give event listener and manager time to process tx
    sleep(test_configuration.default_sleep_time_interval)
    assert ETHSwap.objects(tx_hash=tx_hash).count() == 1  # verify swap event recorded

    sleep(1)
    # check signers were notified of the tx and signed it
    assert Signatures.objects().count() == len(scrt_signers)

    # give time for manager to process the signatures
    sleep(test_configuration.default_sleep_time_interval + 2)
    assert ETHSwap.objects().get().status == Status.SWAP_STATUS_SIGNED.value


# TL;DR: Covers from Leader broadcast of signed tx to scrt swap tx submission on smart contract (withdraw)
# Components tested:
# 1. Leader broadcast to scrt multi-signed mint
# 2. Secret Contract "mint"
def test_2(scrt_leader, test_configuration, contract, web3_provider, scrt_signers):
    # Note: :param ethr_signers: is here only so it will be created before test_3

    # give scrt_leader time to multi-sign already existing signatures
    sleep(test_configuration.default_sleep_time_interval + 3)
    assert ETHSwap.objects().get().status == Status.SWAP_STATUS_SUBMITTED.value

    # get tx details
    tx_hash = ETHSwap.objects().get().tx_hash
    _, log = event_log(tx_hash, ['Swap'], web3_provider, contract.contract)
    transfer_amount = web3_provider.fromWei(log.args.value, 'ether')
    dest = log.args.recipient.decode()

    # validate swap tx on ethr delivers to the destination
    balance_query = '{"balance": {}}'
    tx_hash = run(f"docker exec secretdev secretcli tx compute execute {test_configuration.secret_contract_address} "
                  f"'{balance_query}' --from {dest} -b block -y | jq '.txhash'", shell=True, stdout=PIPE)
    tx_hash = tx_hash.stdout.decode().strip()[1:-1]

    res = run(f"docker exec secretdev secretcli q compute tx {tx_hash} | jq '.output_log' | jq '.[0].attributes' "
              f"| jq '.[3].value'", shell=True, stdout=PIPE).stdout.decode().strip()[1:-1]
    end_index = res.find(' ')
    # TODO: once swap is working, fix it
    # amount = Decimal(res[:end_index])

    # assert abs(transfer_amount - amount) < 1
    # end of ethr to scrt validation


# covers EthrLeader tracking of swap events in scrt and creating submission event in Ethereum
# ethr_signers are here to respond for leader's submission
def test_3(ethr_leader, test_configuration, ethr_signers):
    # Generate swap tx on secret network
    swap = {"swap": {"amount": str(TRANSFER_AMOUNT), "network": "Ethereum", "destination": ethr_leader.default_account}}
    # TODO: once multisig swap work, change the source of swap here

    tx_hash = run(f"secretcli tx compute execute {test_configuration.secret_contract_address} "
                  f"'{json.dumps(swap)}' --from t1 -y", shell=True, stdout=PIPE, stderr=PIPE)
    tx_hash = json.loads(tx_hash.stdout)['txhash']
    # TODO: verify tx_hash

    # Verify that leader recognized the burn tx
    sleep(test_configuration.default_sleep_time_interval + 4)
    assert 0 == Management.last_processed(Source.scrt.value, ethr_leader.logger)

    # Give ethr signers time to handle the scrt swap tx (will be verified in test_4
    sleep(test_configuration.default_sleep_time_interval + 1)


# TL;DR: EthrSigner event response and multisig logic
# Components tested:
# 1. EthrSigner - confirmation and offline catchup
# 2. SmartContract multisig functionality
def test_4(event_listener, contract, web3_provider, ether_accounts, test_configuration, ethr_leader):
    # To allow the new EthrSigner to "catch up", we start it after the event submission event in Ethereum
    private_key = ether_accounts[-1].privateKey
    address = ether_accounts[-1].address
    eth_signer = EthrSigner(event_listener, web3_provider, contract, private_key, address, test_configuration)

    sleep(test_configuration.default_sleep_time_interval)
    # Validate the tx is confirmed in the smart contract
    last_nonce = Management.last_processed(Source.scrt.value, eth_signer.logger)
    assert eth_signer.contract.contract.functions.confirmations(last_nonce, eth_signer.default_account).call()


def increase_block_number(web3_provider: Web3, increment: int) -> True:
    # Creates arbitrary tx on the chain to increase the last block number
    for i in range(increment):
        web3_provider.eth.sendTransaction({
            'from': web3_provider.eth.coinbase,
            'to': web3_provider.eth.accounts[1],
            'value': 100
        })
    return True
