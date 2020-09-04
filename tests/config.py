from os import path

import tests
from src.util.common import module_dir

db_name = "test_db"
secret_contract_address = "secret1h492k6dvfqcuraa935p7laaz203rz5546s0n8k"
signatures_threshold = 3
manager_sleep_time_seconds = 5.0
provider_address = "wss://ropsten.infura.io/ws/v3/e5314917699a499c8f3171828fac0b74"
# contract_address = "0xfc4589c481538f29ad738a13da49af79d93ecb21"
blocks_confirmation_required = 12
default_sleep_time_interval = 5.0
tests_dir, _ = path.split(module_dir(tests))
deployment_dir = path.join(tests_dir, 'deployment')
enclave_key = path.join(deployment_dir, "io-master-cert.der")
enclave_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
chain_id = "enigma-testnet"
multisig_acc_addr = "dynamic update"
