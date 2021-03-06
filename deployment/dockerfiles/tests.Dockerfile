FROM ubuntu:focal

RUN apt-get -qq -y update && \
    apt-get -qq -y upgrade && \
    DEBIAN_FRONTEND=noninteractive apt-get -qq -y install \
        wget \
        nano \
        git \
        make \
        sudo \
        python3-pip \
        mongodb \
        nodejs \
        bash-completion && \
    apt-get -y autoclean && \
    apt-get -y autoremove && \
    rm -rf /var/lib/apt-get/lists/*


RUN npm install -g ganache-cli

RUN wget -O secretcli https://github.com/enigmampc/SecretNetwork/releases/download/v1.0.2/secretcli-linux-amd64
RUN chmod +x ./secretcli
RUN cp ./secretcli /usr/bin

WORKDIR EthereumBridge/

COPY requirements.txt requirements.txt
COPY requirements-dev.txt requirements-dev.txt

RUN pip3 install -r requirements.txt
RUN pip3 install -r requirements-dev.txt

COPY . .

# To run leader:
CMD python3 -m pytest tests/