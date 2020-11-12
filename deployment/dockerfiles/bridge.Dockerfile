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
        bash-completion && \
    apt-get -y autoclean && \
    apt-get -y autoremove && \
    rm -rf /var/lib/apt-get/lists/*


RUN wget -O secretcli https://github.com/enigmampc/SecretNetwork/releases/download/v1.0.3/secretcli-linux-amd64
RUN chmod +x ./secretcli
RUN cp ./secretcli /usr/bin

RUN apt-get install -y softhsm

RUN pip3 install supervisor

WORKDIR EthereumBridge/

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

COPY . .

COPY deployment/config/supervisord.conf /etc/supervisor/supervisord.conf
COPY deployment/config/softhsm2.conf /etc/softhsm/softhsm2.conf

ENTRYPOINT supervisord -c /etc/supervisor/supervisord.conf