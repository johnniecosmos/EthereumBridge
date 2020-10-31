# https://prices.compound.finance/
import json
import aiohttp
from aiohttp.client_exceptions import ClientConnectionError
from aiohttp.web_exceptions import HTTPError

from src.util.coins import Coin, Currency
from src.util.oracle.price_source_base import PriceSourceBase





class CompoundPriceOracle(PriceSourceBase):

    __API_URL = "https://www.etherchain.org/api/gasPriceOracle"

    coin_map = {Coin.Zx: "ZRX",
                Coin.Compound: "COMP",
                Coin.Ethereum: "ETH",
                Coin.Dai: "DAI"}

    currency_map = {Currency.USD: "usd"}

    def _base_url(self):
        return f'{self.__API_URL}'

    async def price(self, coin: Coin, currency: Currency) -> float:
        url = self._base_url()
        try:
            coin_str = self._coin_to_str(coin)
            currency_str = self._currency_to_str(currency)
        except IndexError as e:
            # log not found
            raise ValueError(f"Coin or currently not supported: {e}")

        try:
            async with aiohttp.ClientSession().get(url, raise_for_status=True) as resp:
                resp_json = await resp.json()
                cbase_price = resp_json["coinbase"]["prices"][coin_str]
                okex_price = resp_json["okex"]["prices"][coin_str]

                return (float(cbase_price) + float(okex_price)) / 2
        except (ConnectionError, ClientConnectionError, HTTPError, json.JSONDecodeError):
            pass

    async def x_rate(self, coin1: Coin, coin2: Coin):
        pass