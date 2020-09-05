#!/bin/bash
# Overrides ANY account t1...t{$threshold}
# Overrides multisig account ms{$threshold}

export SGX_MODE=SW

if (("$#" != 2)); then
  echo "Usage: <threshold> <base_dir>"
  exit 1
fi

threshold=$1
keys_directory="$2/keys"
base_dir=$2
deployment_directory="$base_dir/deployment"

mkdir -p "$keys_directory"
mkdir -p "$deployment_directory"

# Setup secretcli configuration
secretcli config chain-id enigma-testnet
secretcli config output json
secretcli config indent true
secretcli config trust-node true

# query register creates cert files in the path of execution
(cd "$deployment_directory" && secretcli query register secret-network-params)

# Create accounts and save output to $keys_directory
for ((i = 1; i <= $1; i++)); do
  accounts="t$i,$accounts"
  echo y | secretcli keys add "t$i" &>"$keys_directory/t$i.json"
done
accounts=${accounts::-1}

# Create multisig account if it doesn't exist
echo y | secretcli keys add "--multisig=$accounts" "--multisig-threshold=$threshold" "ms$threshold" &>"$keys_directory/ms$threshold.json"

# Send money to signing accounts
moneyAddr=$(docker exec secretdev secretcli keys show a -a)
for ((i = 1; i <= threshold; i++)); do
  signerAddr=$(secretcli keys show "t$i" -a)
  docker exec -it secretdev secretcli tx send -y "$moneyAddr" "$signerAddr" 10000000uscrt -b block
done

# Send money to multisig account
multisigAddr=$(secretcli keys show "ms$threshold" -a)
docker exec -it secretdev secretcli tx send -y "$moneyAddr" "$multisigAddr" 10000000uscrt -b block
