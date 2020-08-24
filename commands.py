create_multisign_account = "secretcli keys add --multisig={accounts} --multisig-threshold={threshold} {account_name}"

unsigned_tx = "secretcli tx send {acount_name} $(secretcli keys show -a t2) 1000uscrt --generate-only > unsignedTx.json"

sign_tx = "secretcli tx sign {unsigned_tx_path} --multisig {multi_sig_account}" \
          " --from={account_name} --output-document=p1sig.json"

multisign = "secretcli tx multisign {unsigned_tx_path} {multi_sig_account} {signed_json} > {multisig_path}"

broadcast = "secretcli tx broadcast {multisig_path}"
