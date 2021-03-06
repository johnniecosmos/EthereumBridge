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
docker_name="secretdev"

mkdir -p "$keys_directory"
mkdir -p "$deployment_directory"

# Setup secretcli configuration
secretcli config chain-id enigma-pub-testnet-3
secretcli config output json
secretcli config keyring-backend test
secretcli config indent true
secretcli config trust-node true
secretcli config node tcp://localhost:26657

# query register creates cert files in the path of execution
(cd "$deployment_directory" && secretcli query register secret-network-params)

# Create accounts and save output to $keys_directory
for ((i = 1; i <= $1; i++)); do
  accounts="t$i,$accounts"
  echo y | secretcli keys add "t$i" &>"$keys_directory/t$i.json"
done
accounts=${accounts::-1}

# Create multisig account
echo y | secretcli keys add "--multisig=$accounts" "--multisig-threshold=$threshold" "ms$threshold" &>"$keys_directory/ms$threshold.json"

# Send money to signing accounts
moneyAddr=$(docker exec secretdev secretcli keys show a -a)
for ((i = 1; i <= threshold; i++)); do
  signerAddr=$(secretcli keys show "t$i" -a)
  docker exec -it secretdev secretcli tx send -y "$moneyAddr" "$signerAddr" 10000000000uscrt -b block
done

# Send money to multisig account
multisigAddr=$(secretcli keys show "ms$threshold" -a)
docker exec -it secretdev secretcli tx send -y "$moneyAddr" "$multisigAddr" 1000000000uscrt -b block

# copy contract to docker container
scrt_contract="$base_dir/../src/contracts/secret/token.wasm.gz"
docker cp "$scrt_contract" "$docker_name:/token.wasm.gz"

scrt_contract="$base_dir/../src/contracts/secret/swap.wasm.gz"
docker cp "$scrt_contract" "$docker_name:/swap.wasm.gz"

# store contract on the chain
docker exec -it secretdev secretcli tx compute store "/token.wasm.gz" --from a --gas 2000000 -b block -y

docker exec -it secretdev secretcli tx compute store "/swap.wasm.gz" --from a --gas 2000000 -b block -y

secretcli query compute list-code

## get the admin address
#a_addr=$(docker exec -it secretdev secretcli keys show a | jq '.address')
#
## init contract as 'a' account admin
#docker exec -it secretdev secretcli tx compute instantiate 1 --label LABEL '{"admin": '$a_addr', "name": "CoinName", "symbol": "SYMBL", "decimals": 6, "initial_balances": []}' --from a -b block -y
#contract_addr=$(secretcli query compute list-contract-by-code 1 | jq '.[0].address')
#echo "contract address: $contract_addr"
