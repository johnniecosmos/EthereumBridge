use cosmwasm_std::{
    to_binary, Api, Binary, Env, Extern, HandleResponse, HumanAddr, InitResponse, Querier,
    StdError, StdResult, Storage, Uint128,
};

use crate::msg::ResponseStatus::Success;
use crate::msg::{HandleAnswer, HandleMsg, InitMsg, QueryAnswer, QueryMsg};
use crate::state::{config, Mint, State, Swap, TokenContractParams, config_read};
use crate::token_messages::TokenMsgs;

pub fn init<S: Storage, A: Api, Q: Querier>(
    deps: &mut Extern<S, A, Q>,
    env: Env,
    msg: InitMsg,
) -> StdResult<InitResponse> {
    let state = State {
        owner: deps.api.canonical_address(&msg.owner)?,
    };

    config(&mut deps.storage).save(&state)?;

    if let Some(address) = msg.token_address {
        if let Some(hash) = msg.code_hash {

            // it will be helpful to just do this here instead of after

            let params = TokenContractParams {
                address: deps.api.canonical_address(&address)?,
                code_hash: hash,
            };

            params.store(&mut deps.storage)?;

            let callback = TokenMsgs::RegisterReceive {
                code_hash: env.contract_code_hash,
                padding: None,
            };

            return Ok(InitResponse {
                messages: vec![callback.to_cosmos_msg(address, params.code_hash)?],
                log: vec![],
            });
        }
    }

    Ok(InitResponse::default())
}

pub fn handle<S: Storage, A: Api, Q: Querier>(
    deps: &mut Extern<S, A, Q>,
    env: Env,
    msg: HandleMsg,
) -> StdResult<HandleResponse> {
    match msg {
        HandleMsg::SetTokenAddress {
            address, code_hash, ..
        } => set_token_contract(deps, env, address, code_hash),
        HandleMsg::MintFromExtChain {
            address,
            identifier,
            amount,
            ..
        } => mint_token(deps, env, address, identifier, amount),
        HandleMsg::Receive { amount, msg, sender, .. } => burn_token(deps, env, sender, amount, msg),
    }
}

fn mint_token<S: Storage, A: Api, Q: Querier>(
    deps: &mut Extern<S, A, Q>,
    _env: Env,
    address: HumanAddr,
    identifier: String,
    amount: Uint128,
) -> StdResult<HandleResponse> {
    let params = TokenContractParams::load(&deps.storage).map_err(|_e| {
        StdError::generic_err("You fool you must set the token contract parameters first")
    })?;

    let mint_store = Mint {
        address: deps.api.canonical_address(&address)?,
        identifier,
        amount,
    };
    mint_store.store(&mut deps.storage)?;

    let contract_addr = deps.api.human_address(&params.address)?;
    let mint_msg = TokenMsgs::Mint {
        amount,
        address: address.clone(),
        padding: None,
    };

    Ok(HandleResponse {
        messages: vec![mint_msg.to_cosmos_msg(contract_addr, params.code_hash)?],
        log: vec![],
        data: Some(to_binary(&HandleAnswer::MintFromExtChain {
            status: Success,
        })?),
    })
}

fn burn_token<S: Storage, A: Api, Q: Querier>(
    deps: &mut Extern<S, A, Q>,
    env: Env,
    sender: HumanAddr,
    amount: Uint128,
    msg: Option<Binary>,
) -> StdResult<HandleResponse> {
    // validate that this is a callback from the token contract
    let params = TokenContractParams::load(&deps.storage).map_err(|_e| {
        StdError::generic_err("You fool you must set the token contract parameters first")
    })?;

    if params.address != deps.api.canonical_address(&env.message.sender)? {
        return Err(StdError::generic_err(
            "Called receive function from invalid address",
        ));
    }

    // get params from receive callback msg
    let destination = msg.unwrap().to_string();

    let source = sender.to_string();
    let token = env.message.sender;
    // store the swap details
    let mut swap_store = Swap {
        source,
        amount,
        destination,
        token,
        nonce: 0, // gets automatically set by .store()
    };
    let nonce = swap_store.store(&mut deps.storage)?;

    // create secret-20 burn message
    let burn = TokenMsgs::Burn {
        amount,
        padding: None,
    };

    // send secret-20 burn message to token contract
    let contract_addr = deps.api.human_address(&params.address)?;
    Ok(HandleResponse {
        messages: vec![burn.to_cosmos_msg(contract_addr, params.code_hash)?],
        log: vec![],
        data: Some(to_binary(&HandleAnswer::Receive {
            status: Success,
            nonce,
        })?),
    })
}

pub fn set_token_contract<S: Storage, A: Api, Q: Querier>(
    deps: &mut Extern<S, A, Q>,
    env: Env,
    address: HumanAddr,
    code_hash: String,
) -> StdResult<HandleResponse> {

    let params = config_read(&deps.storage).load()?;

    if params.owner != deps.api.canonical_address(&env.message.sender)? {
        return Err(StdError::generic_err(
            "Cannot set token from non owner address",
        ));
    }

    let params = TokenContractParams {
        address: deps.api.canonical_address(&address)?,
        code_hash,
    };

    params.store(&mut deps.storage)?;

    let callback = TokenMsgs::RegisterReceive {
        code_hash: env.contract_code_hash,
        padding: None,
    };

    Ok(HandleResponse {
        messages: vec![callback.to_cosmos_msg(address, params.code_hash)?],
        log: vec![],
        data: Some(to_binary(&HandleAnswer::SetTokenAddress {
            status: Success,
        })?),
    })
}

pub fn query<S: Storage, A: Api, Q: Querier>(
    deps: &Extern<S, A, Q>,
    msg: QueryMsg,
) -> StdResult<Binary> {
    match msg {
        QueryMsg::Swap { nonce } => query_swap(deps, nonce),
        QueryMsg::MintById { identifier } => query_mint(deps, identifier),
    }
}

pub fn query_swap<S: Storage, A: Api, Q: Querier>(
    deps: &Extern<S, A, Q>,
    nonce: u32,
) -> StdResult<Binary> {
    let swap = Swap::get(&deps.storage, nonce)?;

    Ok(to_binary(&QueryAnswer::Swap { result: swap })?)
}

pub fn query_mint<S: Storage, A: Api, Q: Querier>(
    deps: &Extern<S, A, Q>,
    identifier: String,
) -> StdResult<Binary> {
    let mint = Mint::exists(&deps.storage, &identifier)?;

    Ok(to_binary(&QueryAnswer::Mint { result: mint })?)
}

#[cfg(test)]
mod tests {}
