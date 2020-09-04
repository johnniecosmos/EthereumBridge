if (("$#" != 2))
then
  echo "Usage: <threshold> <base_dir>"
  exit 1
fi

threshold=$1
keys_directory="$2/keys"
deployment_directory="$2/deployment"

mkdir -p "$keys_directory"
mkdir -p "$deployment_directory"

# Setup secretcli configuration
secretcli config chain-id enigma-testnet
secretcli config output json
secretcli config indent true
secretcli config trust-node true

# query register creates cert files in the path of execution
(cd "$deployment_directory" && secretcli query register secret-network-params)

# Create accounts if they do not exist and save output to $keys_directory
for (( i=1; i <= $1; i++ ))
do
  accounts="t$i,$accounts"
  if [ ! -e  "$keys_directory/t$i.json" ]; then
  secretcli keys add t$i &> "$keys_directory/t$i.json"
  fi
done
accounts=${accounts::-1}

# Create multisig account if it doesn't exist
if [ ! -e  "$keys_directory/ms$threshold.json" ]; then
    secretcli keys add "--multisig=$accounts" "--multisig-threshold=$threshold" "ms$threshold" &> "$keys_directory/ms$threshold.json"
fi

# Send money to signing accounts
moneyAddr=$(docker exec secretdev secretcli keys show a -a)
for (( i=1; i <= threshold; i++ ))
do
  signerAddr=$(secretcli keys show "t$i" -a)
  docker exec -it secretdev secretcli tx send -y "$moneyAddr" "$signerAddr" 10000000uscrt -b block
done

# Send money to multisig account
multisigAddr=$(secretcli keys show "ms$threshold" -a)
docker exec -it secretdev secretcli tx send -y "$moneyAddr" "$multisigAddr" 10000000uscrt -b block
