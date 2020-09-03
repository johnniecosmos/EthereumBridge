# args:
# $1 = number of signing accounts


# Setup secretcli with configuration for unit-testing
secretcli config chain-id 1
secretcli config node tcp://127.0.0.1:26657
secretcli config output json
secretcli config indent true
secretcli config trust-node true
#secretcli query register secret-network-params

keys_directory="$(dirname "${BASH_SOURCE[0]}")/keys"
# Make keys directory if doesn't exist
mkdir -p "$keys_directory"

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
if [ ! -e  "$keys_directory/ms$1.json" ]; then
    secretcli keys add "--multisig=$accounts" "--multisig-threshold=$1" "ms$1" &> "$keys_directory/ms$1.json"
fi