from os import path

import main

signing_accounts = ["account1", "account2"]
multisig_account = "name"
threshold = 2
manager_sleep_time_seconds = 5.0
contract_address = "0xfc4589c481538f29ad738a13da49af79d93ecb21"
provider_address = "wss://ropsten.infura.io/ws/v3/e5314917699a499c8f3171828fac0b74"
blocks_confirmation_required = 12

project_base_path, _ = path.split(main.__file__)
secret_cli = path.join(project_base_path, "temp", "secretcli.exe")
