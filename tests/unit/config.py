from os import path
from tests.unit import deployment

db_name = "test_db"
secret_contract_address = "secret1h492k6dvfqcuraa935p7laaz203rz5546s0n8k"
signatures_threshold = 2
manager_sleep_time_seconds = 5.0
provider_address = "wss://ropsten.infura.io/ws/v3/e5314917699a499c8f3171828fac0b74"
# contract_address = "0xfc4589c481538f29ad738a13da49af79d93ecb21"
blocks_confirmation_required = 12
default_sleep_time_interval = 5.0
deployment_dir, _ = path.split(deployment.__file__)
enclave_key = path.join(deployment_dir, "io-master-cert.der")
enclave_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
chain_id = 2
multisig_acc_addr = "secret1gze003z96mmrctjtdpesww3z7sg4u6dmxpue0m"
