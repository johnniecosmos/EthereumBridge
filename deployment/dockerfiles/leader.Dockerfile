FROM enigmampc/ubuntu18python:3.8

RUN wget -O secretcli https://github.com/enigmampc/SecretNetwork/releases/download/v1.0.2/secretcli-linux-amd64
RUN chmod +x ./secretcli
RUN cp ./secretcli /usr/bin

RUN pip3 install \
      --no-index \
      --find-links=/root/wheels \
      supervisor

WORKDIR EthereumBridge/

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt


# To run leader:
python3 ./deployment/testnet/ethr_swap/leader/main.py