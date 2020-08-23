pragma solidity >0.5.99 <0.8.0;  //this is random, check it.

contract EthSwap{
    address public minter;
    uint256 public balance;
    mapping(uint256 => bool) public nounces;

    event Swap(address from, bytes to, uint256 amount);
    event Credit(address to, uint256 amount);


      constructor() {
        minter = msg.sender;
    }

    function swap(bytes memory  recipient, uint256 amount) public{
        require(
            address(msg.sender).balance >= amount,
            "No available funds."
            );
        emit Swap(msg.sender, recipient, amount);
        balance += amount;
    }

    function credit(address payable recipient, uint256 amount, uint256 nounce) public{
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
            address(this).balance >= amount,
            "Not enough funds to approve tx."
            ); 
        recipient.transfer(amount);
        emit Credit(recipient, amount);
        balance -= amount;

    }
}