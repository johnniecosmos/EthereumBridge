import aiohttp

from src.util.oracle.gas_source_base import GasSourceBase


class POAGasOracle(GasSourceBase):
    __API_URL = "https://gasprice.poa.network/"

    def _base_url(self):
        return f'{self.__API_URL}'

    async def gas_price(self) -> int:
        url = self._base_url()
        # this opens a new connection each time. It's possible to restructure with sessions, but then the session needs
        # to live inside an async context, and I don't think it's necessary right now
        async with aiohttp.ClientSession().get(url, raise_for_status=True) as resp:
            resp = await resp.json()
            # To convert the provided values to gwei, divide by 10
            # https://docs.ethgasstation.info/gas-price
            value = resp["standard"]
            return int(value)
