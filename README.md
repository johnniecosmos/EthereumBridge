# Ethereum Bridge
This is a quick guide that explains how to setup a bridge between Secret and Ethereum.

## General

The Ethereum bridge transfers between assets on the Ethereum network (ETH/ERC20) and Secret tokens, specified by the 
SNIP-20 spec. The bridge is bi-directional, so those SNIP-20 assets can then be redeemed for their Ethereum equivalent.

### Architecture
The bridge uses a leader->signer architecture. The leader is responsible for watching the chain for new events. Once a 
new event is found, a transaction is proposed. 

The signers then take that proposed transaction, __validate that the proposed tx was indeed triggered by an on-chain event__
and then sign (or broadcast an approval for) the transaction.

On the ETH side, once the amount of signers passes the threshold it is executed automatically, while on the SCRT side we 
need an extra step done by the leader - broadcasting the signed transaction. The difference is due to how multisig is
implemented on the different networks.

On the SCRT side each pair of assets (e.g. ETH<->secretETH) is managed by are 2 secret contracts. The first is the SNIP-20
contract itself, which manages the token. This is the contract that a user will interact with to manage his token. That way
for the user there is no difference between a bridged asset, and any other SNIP-20 asset (secret-secret, for instance) 

In the future the bridge may also scale to other networks beyond Ethereum

## Setup

### Tests

### Dependencies 
* jq
* secretcli 
* ganache-cli running locally on port 8545
* mongodb on port 27017
* Secret network dev environment

#### Run ganache

```ganache-cli```

#### Run secret network dev environment

```docker run -it --rm -p 26657:26657 -p 26656:26656 -p 1317:1317 --name secretdev enigmampc/secret-network-sw-dev:v1.0.2```

#### Make sure secretcli is runnable

You should be able to run secretcli directly (copy it to /usr/bin/ or something)
```
secretcli status
```

#### Install dev dependencies

```
pip install -r requirements-dev.txt
```

#### Run Tests

```sh

python -m pytest tests/
```

### Run Local bridge

#### Upload Eth contracts and Secret Contracts

Use the scripts in ./deployment/deploy.py to deploy your eth & scrt contracts

#### Run the dockerfile

Use the example docker-compose file to customize your leader & signer parameters

## Manual swap


### Secret20 -> Ethereum/ERC-20 

Call the `send` method of the Secret20 token, with the recipient being our multisig address, and the `msg` field containing the
__base64 encoded__ ethereum address

```
secretcli tx compute execute '{"send": {"recipient": "secret1hx84ff3h4m8yuvey36g9590pw9mm2p55cwqnm6", "amount": "200", "msg": "MHhGQmE5OGFEMjU2QTM3MTJhODhhYjEzRTUwMTgzMkYxRTNkNTRDNjQ1"}}' --label <secret-contract-label> --from <key> --gas 350000'
```

### Ethereum -> Secret20

Call the method `swap` on our MultiSig contract, specifying the amount sent in the `value`, and the destination in the arguments.
Python example (see: swap_eth.py):
```python
    ...
    tx_hash = send_contract_tx(multisig_wallet.contract, 'swap',
                               account, bytes.fromhex(private_key), "secret13l72vhjngmg55ykajxdnlalktwglyqjqv9pkq4", value=200)
    ...
```

### ERC20 -> Secret20

Call the `transfer` function, with `to` being our MultiSig contract, `value` caontaining the amount of tokens, and `recipient` being the address on the secret network

```python
    tx_hash = erc20_contract.contract.functions.transfer("0x913BD292C1fbd164Bb61436aa1B026C8131104fd",
                                                         200,
                                                         "secret13l72vhjngmg55ykajxdnlalktwglyqjqv9pkq4")...
```


###### Config Parameters

All these parameters can be overwritten by setting an environment variable with the same name. Set common variables in one
of the files in the ./config/ directory, and the rest by setting environment variables

* db_name - name of database
* app_data - path to local cache directory (no need to touch this in most cases)
* signatures_threshold - number of signatures required to authorize transaction 
* eth_confirmations - number of blocks to wait on ethereum before confirming transactions
* eth_start_block - block number to start scanning events from  
* sleep_interval - time to sleep between 
* network - name of ethereum network
* chain_id - secret network chain-id
* multisig_wallet_address - Ethereum multisig contract address
* secret_token_address - address of SNIP-20 secret contract token we are minting
* secret_swap_contract_address - address of secret contract handling our swaps
* secret_token_name - name of secret token (not required)
* code_hash - code hash of the secret contract handling our swaps
* KEYS_BASE_PATH - path to directory with secret network key, and transactional key (id_tx_io.json)
* SECRETCLI_HOME - path to secretcli config directory (/home/{user}/.secretcli)
* account - ethereum address
* private_key - ethereum private key
* secret_node - address of secret network rpc node
* eth_node_address - address of ethereum node (or service like infura)
* enclave_key - path to enclave key
* multisig_acc_addr - secret network multisig address
* multisig_key_name - secret network multisig name
* secret_signers - list of the public keys of addresses that comprise the address in `multisig_acc_addr`

Example settings:
```json
{
  "db_name": "test_db",
  "app_data": ".bridge_data",
  "signatures_threshold": 3,
  "eth_confirmations": 2,
  "eth_start_block": 8880990,
  "sleep_interval": 5.0,
  "network": "ropsten",
  "chain_id": "holodeck",
  "multisig_wallet_address": "0x913BD292C1fbd164Bb61436aa1B026C8131104fd",
  "secret_token_address": "secret1ljptw8mf5wk9n69j2v5vl4w2laqlrgspxykanp",
  "secret_swap_contract_address": "secret1hx84ff3h4m8yuvey36g9590pw9mm2p55cwqnm6",
  "secret_token_name": "seth",
  "code_hash": "309757D609FB932B5DD0E101A2D018E80FC11347B3A8EB285B826B0E2CBDA236",
  "KEYS_BASE_PATH": "/EthereumBridge/tkeys",
  "SECRETCLI_HOME": "/root/.secretcli",
  "secret_node": "tcp://bootstrap.secrettestnet.io:26657",
  "eth_node_address": "https://ropsten.infura.io/v3/89693d2faa364dfabc22b5635cb85a21",
  "enclave_key": "io-master-cert.der",
  "viewing_key": "api_key_A90Mw0L31a4Uxm5E1wr+woYq8vuZfnzTpnH6ivyajb4=",
  "multisig_acc_addr": "secret18g2pvlz2ess848qkfwert28a2n7xqknjxjgesd",
  "multisig_key_name": "ms3",
  "secret_signers": ["secretpub1addwnpepqwamxgvaeayyhlsh5htwx9z8vh40vnm5fwlr5axzn6jheeyv3yxhv2qk5p7", "secretpub1addwnpepqf080zg7qhwh7wx777jfnyaemp366778edfc5yt7238m3vk03a75ypdtyzk", "secretpub1addwnpepqfr4h7p7ylhyjuv0fcef22wu28sgdqljhnz9dtrpafhs4hdkn4r9z3w2z2n"]
}
```
