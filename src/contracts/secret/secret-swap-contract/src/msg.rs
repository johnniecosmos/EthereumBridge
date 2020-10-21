use crate::state::Swap;
use cosmwasm_std::{Binary, HumanAddr, Uint128};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, JsonSchema)]
pub struct InitMsg {
    pub owner: HumanAddr,
    pub token_address: Option<HumanAddr>,
    pub code_hash: Option<String>,
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum HandleMsg {
    SetTokenAddress {
        address: HumanAddr,
        code_hash: String,
    },
    //Receive { destination: String, nonce: u64, amount: Uint128, padding: Option<String> },
    Receive {
        sender: HumanAddr,
        msg: Option<Binary>,
        amount: Uint128,
    },
    MintFromExtChain {
        address: HumanAddr,
        identifier: String,
        amount: Uint128,
        padding: Option<String>,
    },
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum QueryMsg {
    // GetCount returns the current count as a json-encoded number
    Swap { nonce: u32 },
    MintById { identifier: String },
}

#[derive(Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum HandleAnswer {
    // Native
    SetTokenAddress { status: ResponseStatus },
    Receive { status: ResponseStatus, nonce: u32 },
    MintFromExtChain { status: ResponseStatus },
}

#[derive(Serialize, Deserialize, Clone, PartialEq, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum ResponseStatus {
    Success,
    Failure,
}

#[derive(Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum QueryAnswer {
    Swap { result: Swap },
    Mint { result: bool },
}
