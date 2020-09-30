# management
db_name = "test_db"
app_data = ".bridge_test"
logger_name = "test logger"

# app settings
signatures_threshold = 2
blocks_confirmation_required = 2
ethr_signer_start_block = 8781958

default_sleep_time_interval = 5.0
chain_id = "holodeck"
multisig_wallet_address = "0xCA4666D11bFc85300fd4cE98fD970Bdc98dCcc8B"
secret_contract_address = "secret1uwcjkghqlz030r989clzqs8zlaujwyphwkpq0n"
code_hash = "666e3abc202103ae43a5bb4b1e7a9b542ffd69e96eafdbc071dc9a8df8526945"
provider_address = "https://ropsten.infura.io/v3/c1b139e430f14107b851487a6e96b363"
enclave_key = "/home/guy/Workspace/dev/EthereumBridge/deployment/testnet/io-master-cert.der"

# used for erc20 swap
mint_token = True
token_contract_addr = "0x06526C574BA6e45069057733bB001520f08b59ff"

# ~~~~~~~~~~~~~~~~~~ user settings ~~~~~~~~~~~~~~~~~~

# ~~~~~~~~~~~~~~~~~~ ethr ~~~~~~~~~~~~~~~~~~
# the ethr leader is one of the signers, so we neglect him here
# account 2
signer_acc_addr_2 = "0xE54b62C7c0103465316D49a2620ba32C703c60cE"
signer_key_2 = "6e9b1de69b263184bae321e8022453b478fab91fca0d7621d558f477336570e8"

# account 3
signer_acc_addr_3 = "0xaeA9263ae4cC574b875be2eDF12df1FC86055f97"
signer_key_3 = "39e449a85306edbc5231fe5a6fa4dd1bbbf690526d6f2901ee9de9b32b0d2d32"

# ~~~~~~~~~~~~~~~~~~ scrt ~~~~~~~~~~~~~~~~~~
viewing_key = "api_key_bxa1ySwaFrCacBvHm73PMINyTwB+6GMZXMvZlnwOGgM="
multisig_acc_addr = "secret1zh8w8q6tkqrrpz064c0xpjgkeyvnzvg3edg4cl"
multisig_key_name = "ms2"

# signer 1
scrt_signer_addr_1 = "secret1sf7zjlg7u6uw0hyypy3akw3qtryt3p4e2gknxa"
signer_key_name_1 = "signer1"

# signer 2
scrt_signer_addr_2 = "secret1vl8hl9agvwhrj57fh249akxem2akcyapxq8y0a"
signer_key_name_2 = "signer2"
