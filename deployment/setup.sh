wget -O secretcli https://github.com/enigmampc/SecretNetwork/releases/download/v1.0.2/secretcli-linux-amd64
chmod +x ./secretcli
cp ./secretcli /usr/bin
secretcli config chain-id holodeck
secretcli config output json
secretcli config indent true
secretcli config node tcp://bootstrap.secrettestnet.io:26657
secretcli config trust-node true
sudo apt update
git clone repo
git checkout -b deployment origin/deployment
cd ./EthereumBridge
sudo apt install python3-pip -y
pip3 install -r ./requirements.txt
# To run leader:
python3 ./deployment/testnet/ethr_swap/leader/main.py
# To run signer:
python3 ./deployment/testnet/ethr_swap/signer/main.py