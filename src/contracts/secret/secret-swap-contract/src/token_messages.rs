use core::fmt;
use cosmwasm_std::{Binary, CosmosMsg, HumanAddr, StdError, StdResult, Uint128, WasmMsg};
use serde::{Deserialize, Serialize};
use serde_json;

#[derive(Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum TokenMsgs {
    Burn {
        amount: Uint128,
        padding: Option<String>,
    },
    Mint {
        amount: Uint128,
        address: HumanAddr,
        padding: Option<String>,
    },
    RegisterReceive {
        code_hash: String,
        padding: Option<String>,
    },
}

impl fmt::Display for TokenMsgs {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match *self {
            TokenMsgs::Burn { .. } => write!(f, "Burn"),
            TokenMsgs::Mint { .. } => write!(f, "Mint"),
            TokenMsgs::RegisterReceive { .. } => write!(f, "RegisterReceive"),
        }
    }
}

impl TokenMsgs {
    pub fn to_cosmos_msg(&self, contract: HumanAddr, code_hash: String) -> StdResult<CosmosMsg> {
        let msg_str = serde_json::to_string(&self).map_err(|e| StdError::GenericErr {
            msg: format!("Failed to serialize {} message: {}", &self, e.to_string()),
            backtrace: None,
        })?;

        return Ok(CosmosMsg::Wasm(WasmMsg::Execute {
            contract_addr: contract,
            callback_code_hash: code_hash,
            msg: Binary(msg_str.as_bytes().to_vec()),
            send: vec![],
        }));
    }
}
