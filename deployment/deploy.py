import json
import random
import string
import subprocess

from src.db import database
from src.db.collections.token_map import TokenPairing
from src.util.config import Config
from src.util.web3 import web3_provider

signer_accounts = ['0xA48e330838A6167a68d7991bf76F2E522566Da33', '0x55810874c137605b96e9d2B76C3089fcC325ed5d',
                   '0x984C31d834d1F13CCb3458f4623dB21975FE4892', '0x552B5078a9044688F6044B147Eb2C8DFb538737e']


# def whitelist_token_eth():
#

def add_token(token: str):

    cfg = Config()

    with open('./src/contracts/ethereum/compiled/MultiSigSwapWallet.json', 'r') as f:
        contract_source_code = json.loads(f.read())

    w3 = web3_provider(cfg['eth_node_address'])
    account = w3.eth.account.from_key("0xb84db86a570359ca8a16ad840f7495d3d8a1b799b29ae60a2032451d918f3826")

    contract = w3.eth.contract(address=cfg['multisig_wallet_address'],
                               abi=contract_source_code['abi'],
                               bytecode=contract_source_code['data']['bytecode']['object'])

    nonce = w3.eth.getTransactionCount(account.address, "pending")
    tx = contract.functions.addToken(token)
    raw_tx = tx.buildTransaction(transaction={'from': account.address, 'gas': 3000000, 'nonce': nonce})
    signed_tx = account.sign_transaction(raw_tx)
    tx_hash = w3.eth.sendRawTransaction(signed_tx.rawTransaction)
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    print(f"Done adding token: {tx_receipt=}")


def deploy_eth():

    cfg = Config()

    with open('./src/contracts/ethereum/compiled/MultiSigSwapWallet.json', 'r') as f:
        contract_source_code = json.loads(f.read())

    w3 = web3_provider(cfg['eth_node_address'])
    account = w3.eth.account.from_key("0xb84db86a570359ca8a16ad840f7495d3d8a1b799b29ae60a2032451d918f3826")
    print(f"Deploying on {cfg['network']} from address {account.address}")
    balance = w3.eth.getBalance(account.address, "latest")
    if balance < 1000000000000:
        print("You gotta have some cash dawg")
        return

    # Instantiate and deploy contract
    contract = w3.eth.contract(abi=contract_source_code['abi'], bytecode=contract_source_code['data']['bytecode']['object'])
    tx = contract.constructor(signer_accounts, cfg['signatures_threshold'],)

    nonce = w3.eth.getTransactionCount(account.address, "pending")

    raw_tx = tx.buildTransaction(transaction={'from': account.address, 'gas': 3000000, 'nonce': nonce})

    signed_tx = account.sign_transaction(raw_tx)

    tx_hash = w3.eth.sendRawTransaction(signed_tx.rawTransaction)
    # .transact()
    # Get transaction hash from deployed contract
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    print(f"Deployed at: {tx_receipt.contractAddress}")
    multisig_wallet = w3.eth.contract(address=tx_receipt.contractAddress, abi=contract_source_code['abi'])
    print("All done")


def rand_str(n):
    alphabet = string.ascii_letters + string.digits
    return ''.join(random.choice(alphabet) for i in range(n))


def deploy_scrt():

    configuration = Config()

    # docker exec -it secretdev secretcli tx compute store "/token.wasm.gz" --from a --gas 2000000 -b block -y
    #
    # docker exec -it secretdev secretcli tx compute store "/swap.wasm.gz" --from a --gas 2000000 -b block -y

    multisig_account = configuration["multisig_acc_addr"]
    deployer = "secret1qcz0405jctqvar3e5wmlsj2q5vrehgudtv5nqd"

    tx_data = {"admin": multisig_account, "name": "Coin Name", "symbol": "ETHR", "decimals": 6,
               "initial_balances": [], "config": {}, "prng_seed": "YWE"}

    cmd = f"secretcli tx compute instantiate 1 --label {rand_str(10)} '{json.dumps(tx_data)}'" \
          f" --from t1 -b block -y"
    res = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)

    res = subprocess.run("secretcli query compute list-contract-by-code 1 | jq '.[-1].address'",
                         shell=True, stdout=subprocess.PIPE)
    configuration['secret_token_address'] = res.stdout.decode().strip()[1:-1]

    tx_data = { "owner": multisig_account }

    cmd = f"secretcli tx compute instantiate 2 --label {rand_str(10)} '{json.dumps(tx_data)}'" \
          f" --from t1 -b block -y"
    res = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)

    res = subprocess.run("secretcli query compute list-contract-by-code 2 | jq '.[-1].address'",
                         shell=True, stdout=subprocess.PIPE)
    configuration['secret_swap_contract_address'] = res.stdout.decode().strip()[1:-1]

    res = subprocess.run(f"secretcli q compute contract-hash {configuration['secret_swap_contract_address']}",
                         shell=True, stdout=subprocess.PIPE).stdout.decode().strip()[2:]
    configuration['code_hash'] = res


def configure_db():

    with database("test_db", "cluster0.dka2m.mongodb.net", "leader", "6FXQ3gHXQQAkbpmI"):
        # TokenPairing(src_network="Ethereum", src_coin="ETH", src_address="native",
        #              dst_network="Secret", dst_coin="secret-ETH", dst_address="secret1nk5c3agzt3ytpkl8csfhf4e3qwleauex9ay69t").save()
        TokenPairing.objects().get(src_network="Ethereum", dst_coin="secret-TUSD").update(src_address="0x1cB0906955623920c86A3963593a02a405Bb97fC")
        #
        # TokenPairing(src_network="Ethereum", src_coin="YEENUS", src_address="0xF6fF95D53E08c9660dC7820fD5A775484f77183A",
        #              dst_network="Secret", dst_coin="secret-NUS", dst_address="secret17nfn68fdkvvplr8s0tu7qkhxfw08j7rwne5sl2").save()
        #
        # TokenPairing(src_network="Ethereum", src_coin="TUSD", src_address="native",
        #              dst_network="Secret", dst_coin="secret-TUSD", dst_address="secret1psm5jn08l2ms7sef2pxywr42fa8pay877vpg68").save()


if __name__ == '__main__':
    #deploy_eth()
    #add_token("0xF6fF95D53E08c9660dC7820fD5A775484f77183A")
    configure_db()
    # deploy_scrt()
    # yeenus