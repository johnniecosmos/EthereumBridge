from web3 import Web3


def test_1(manager, leader, signer_accounts, web3_provider, test_configuration):
    # send contract tx
    # somehow send enough tx to create blocks (# of confirmation required)
    # verify recorded by manager
    # verify signed
    # verify multisig
    # verify money SCRT
    # verify status submitted updated

    # Send contract tx

    assert increase_block_number(web3_provider, test_configuration.blocks_confirmation_required)


def increase_block_number(web3_provider: Web3, increment: int) -> True:
    current = web3_provider.eth.getBlock('latest').number
    # Creates stupid tx on the chain to increase the last block number
    for i in range(increment):
        web3_provider.eth.sendTransaction({
            'from': web3_provider.eth.coinbase,
            'to': web3_provider.eth.accounts[1],
            'value': 100
        })
    return web3_provider.eth.getBlock('latest').number - current >= 12
