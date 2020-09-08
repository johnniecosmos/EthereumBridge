pragma solidity >0.5.99 <0.8.0;

contract EthSwap {
    address public minter;
    mapping(uint256 => bool) public nounces; //TODO: Can be converted to last nounce received to save storage?

    event Swap(address from, bytes to, uint256 amount);
    event Credit(address to, uint256 amount);


    constructor() public {
        minter = msg.sender;
    }

    function swap(bytes memory recipient, uint256 amount) payable public {
        require(
            address(msg.sender).balance >= amount,
            "Not enough funds available."
        );
        // TODO: Make sure it burns the ethereum
        emit Swap(msg.sender, recipient, amount);
    }

    function credit(address payable recipient, uint256 amount, uint256 nounce) public {
        // Check validity of address?
        require(
            msg.sender == minter,
            "Only creator can use contract funds to credit of burn in SCRT network."
        );

        require(
            !nounces[nounce],
            "Transaction with same nounce already processed."
        );

        require(
            address(this).balance <= amount,
            "Not enough funds available."
        );

        recipient.transfer(amount);
        emit Credit(recipient, amount);
        // TODO: check if i need both
    }
}
