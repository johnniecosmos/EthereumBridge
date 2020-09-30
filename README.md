# Ethereum Bridge
This is a quick guide that explains how to setup a bridge between Secret and Ethereum.
In the deployment folder you will find suggested deployment configuration and setup for bot the ethr and erc20 options.


## Leader Setup
Components that will be deployed: Manager, EthrLeader, SecretLeader.
Find an example on how to generate in deployment\\*_swap\leader\main.py


## Signer Setup
Components that will be deployed: EthrSigner, SecretSigner.
Find an example on how to generate in deployment\\*_swap\leader\main.py  


##Settings


###Management settings
host - ip\dns of the destination DB  
port - port to which the DB listens  
db_name - name of the db in the mongodb host  
username - user name to access the DB  
password - password to access the DB  


###App settings
logger_name - project logger name (arbitrary)  
signatures_threshold - how many signers are required in order to sign a tx (validators)  
blocks_confirmation_required - how many blocks on ethereum to wait, before treating it as "confirmed".    
default_sleep_time_interval - how long to wait while between chain sampling.  
provider_address - web3 endpoint that will be used to query Ethereum.  
ethr_start_block - the block from which the manager starts scanning for missed tx (in catch_up mode), optional
ethr_signer_start_block - the block from which the signer starts scanning for missed tx (in submission_catch_up),
optional

###Secret network settings
\* more  on how to generate these params bellow, in the how to install section.    
chain_id - the id of the chain to which we connect, used by secretcli.  
secret_contract_address - the address of the deployed contract on the secret network which is responsible of minting.  
code_hash - the hash of the deployed secret contract.  


###MultisigWallet contract settings
multisig_wallet_address - the address of the leader which multisig the tx.  


###Erc20 swap contract settings
mint_token - bool flag (True/False) that indicates if we transfer ethr or erc20 tokens.  
token_contract_addr - if the above is True, should contain the address of the deployed erc20 token contract.  


###EthrSigner/EthrLeader settings
signer_acc_addr - the ethereum wallet address that will be use bt the EthrSigner.  
signer_key - the private key corresponding to the above signer_acc_addr.  


###SecretSigner/SecretLeader settings
enclave_key - the certificate that is used for offline signing.  
viewing_key - viewing key generate to query the secret contract.
multisig_acc_addr - the address that can mint new tokens in Secret.  
multisig_key_name - the name of of the account who's address is multisig_acc_addr.     
scrt_signer_addr - the address of a signer in Secret.  
signer_key_name - the name of the singer account.  


##How to generate the settings
All the commands to deploy/query/create code-hash/viewing_key  on secret are found in the following links:  
https://github.com/enigmampc/secret-secret/tree/swap-burn-mint  
https://github.com/enigmampc/SecretNetwork/blob/master/docs/testnet/deploy-contract.md
  

Ethereum contract deployment can be done with metamask + remix.  


## How to install
setup.sh under deployment will contain the basic configuration, update the relevant params and execute.  

If you run a leader, you will have to import the remote signers keys:
secretcli keys add --pubkey [the multisig public key in bech32 format] [mutisig_account_name]
