from src.util.coins import Coin, Currency


class GasSourceBase:
    __API_URL = ""

    async def gas_price(self) -> int:
        raise NotImplementedError

