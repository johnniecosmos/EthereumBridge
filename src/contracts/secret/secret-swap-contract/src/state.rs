use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use cosmwasm_std::{CanonicalAddr, ReadonlyStorage, StdError, StdResult, Storage, Uint128};
use cosmwasm_storage::{singleton, singleton_read, ReadonlySingleton, Singleton};
use cosmwasm_storage::{PrefixedStorage, ReadonlyPrefixedStorage};

use secret_toolkit::storage::{AppendStore, AppendStoreMut};

pub static CONFIG_KEY: &[u8] = b"config";
pub static TOKEN_CONTRACT_PARAMS_KEY: &[u8] = b"TokenContractParams";
pub static SWAP_KEY: &[u8] = b"swap";
pub static MINT_KEY: &[u8] = b"mint";

#[derive(Serialize, Deserialize, Clone, Debug, JsonSchema)]
pub struct Mint {
    pub identifier: String,
    pub amount: Uint128,
    pub address: CanonicalAddr,
}

impl Mint {
    /// store
    ///
    /// appends a mint message to contract storage. Will return an Ok() if mint is unique and stored successfully
    /// Err() if the store failed, or if the mint already exists
    pub fn store<S: Storage>(&self, store: &mut S) -> StdResult<()> {
        let exists = Self::exists(store, &self.identifier);

        let mut store = PrefixedStorage::new(MINT_KEY, store);
        let mut store = AppendStoreMut::attach_or_create(&mut store)?;

        if exists.is_ok() && exists.unwrap() {
            return Err(StdError::generic_err("Mint already exists"));
        }

        store.push(self)?;
        Ok(())
    }

    pub fn exists<S: ReadonlyStorage>(storage: &S, key: &String) -> StdResult<bool> {
        let store = ReadonlyPrefixedStorage::new(MINT_KEY, storage);

        // Try to access the storage of txs for the account.
        // If it doesn't exist yet, return an empty list of transfers.
        let store = if let Some(result) = AppendStore::<Self, _>::attach(&store) {
            result?
        } else {
            return Ok(false);
        };

        for s in store.iter() {
            if &s?.identifier == key {
                return Ok(true);
            }
        }

        return Ok(false);
    }
}

#[derive(Serialize, Deserialize, Clone, Debug, JsonSchema)]
pub struct Swap {
    pub destination: String,
    pub source: String,
    pub amount: Uint128,
    pub nonce: u32,
}

impl Swap {
    pub fn store<S: Storage>(&mut self, store: &mut S) -> StdResult<u32> {
        let mut store = PrefixedStorage::new(SWAP_KEY, store);
        let mut store = AppendStoreMut::attach_or_create(&mut store)?;

        let nonce = store.len();
        self.nonce = nonce;
        store.push(self)?;
        Ok(nonce)
    }

    pub fn get<S: ReadonlyStorage>(storage: &S, key: u32) -> StdResult<Self> {
        let store = ReadonlyPrefixedStorage::new(SWAP_KEY, storage);

        // Try to access the storage of txs for the account.
        // If it doesn't exist yet, return an empty list of transfers.
        let store = if let Some(result) = AppendStore::<Self, _>::attach(&store) {
            result?
        } else {
            return Err(StdError::generic_err(format!(
                "Failed to get swap for key: {}",
                key
            )));
        };

        store.get_at(key)
    }
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, JsonSchema)]
pub struct TokenContractParams {
    pub address: CanonicalAddr,
    pub code_hash: String,
}

impl TokenContractParams {
    pub fn store<S: Storage>(&self, storage: &mut S) -> StdResult<()> {
        let mut bucket: Singleton<S, TokenContractParams> =
            singleton(storage, TOKEN_CONTRACT_PARAMS_KEY);

        bucket.save(&self)?;

        Ok(())
    }

    pub fn load<S: Storage>(storage: &S) -> StdResult<TokenContractParams> {
        let params: ReadonlySingleton<S, TokenContractParams> =
            singleton_read(storage, TOKEN_CONTRACT_PARAMS_KEY);

        let res = params.load()?;

        Ok(res)
    }
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, JsonSchema)]
pub struct State {
    pub owner: CanonicalAddr,
}

pub fn config<S: Storage>(storage: &mut S) -> Singleton<S, State> {
    singleton(storage, CONFIG_KEY)
}

pub fn config_read<S: Storage>(storage: &S) -> ReadonlySingleton<S, State> {
    singleton_read(storage, CONFIG_KEY)
}
