@fixture(scope="module")
def make_project(db, configuration):
    # init brownie project structure
    project.new(brownie_project_folder)

    # copy contracts to brownie contract folder
    brownie_contracts = os.path.join(brownie_project_folder, 'contracts')

    erc20_contract = '/home/guy/Workspace/dev/EthereumBridge/tests/integration/token_contract/EIP20.sol'
    copy(erc20_contract, os.path.join(brownie_contracts, 'EIP20.sol'))

    multisig_contract = os.path.join(contracts_folder, 'MultiSigSwapWallet.sol')
    copy(multisig_contract, os.path.join(brownie_contracts, 'MultiSigSwapWallet.sol'))

    # for contract in filter(lambda p: p.endswith(".sol"), os.listdir(contracts_folder)):
    #     copy(os.path.join(contracts_folder, contract), os.path.join(brownie_project_folder, 'contracts', contract))
    # copy(os.path.join(contracts_folder, contract), os.path.join(brownie_project_folder, 'contracts', contract))

    # load and compile contracts to project
    brownie_project = project.load(brownie_project_folder, name="IntegrationTests")
    brownie_project.load_config()

    # noinspection PyUnresolvedReferences
    # from brownie.project.IntegrationTests import MultiSigSwapWallet
    network.connect('development')  # connect to ganache cli

    yield network

    # cleanup
    del brownie_project
    sleep(1)
    rmtree(brownie_project_folder, ignore_errors=True)


@fixture(scope="module")
def erc20_contract(make_project, test_configuration, ether_accounts):
    from brownie.project.IntegrationTests import EIP20
    # solidity contract deploy params
    _initialAmount = 100
    _tokenName = 'TN'
    _decimalUnits = 18
    _tokenSymbol = 'TS'

    erc20 = EIP20.deploy(_initialAmount, _tokenName, _decimalUnits, _tokenSymbol,
                         {'from': accounts[0]})
    test_configuration.mint_token = True
    test_configuration.token_contract_addr = str(erc20.address)
    test_configuration.token_abi = '/home/guy/Workspace/dev/EthereumBridge/tests/integration/token_contract/EIP20.json'
    # Note: we don't return here anything, as it's only created for leader's usage through config


@fixture(scope="module")
def event_listener(multisig_wallet, web3_provider, test_configuration):
    listener = EventListener(multisig_wallet, web3_provider, test_configuration)
    yield listener
    listener.stop_event.set()


@fixture(scope="module")
def manager(event_listener, multisig_wallet, multisig_account, test_configuration):
    manager = Manager(event_listener, multisig_wallet, multisig_account, test_configuration)
    yield manager
    manager.stop_signal.set()