"""Crypto price feed implementations."""

import logging
import time
from dataclasses import dataclass

import httpx
import orjson

logger = logging.getLogger(__name__)


@dataclass
class PriceData:
    """Price data container."""

    symbol: str
    price: float
    timestamp: float
    change_24h: float | None = None


class CryptoPriceFeed:
    """Crypto price feed using Binance API."""

    def __init__(self) -> None:
        self.base_url = "https://api.binance.com/api/v3"
        self._cache: dict[str, tuple[PriceData, float]] = {}
        self._cache_ttl = 10  # seconds

    def get_price(self, symbol: str) -> PriceData | None:
        """Get current price for symbol (e.g., 'BTCUSDT')."""
        cache_key = f"price_{symbol}"
        now = time.time()

        # Check cache
        if cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if now - cached_time < self._cache_ttl:
                return cached_data

        try:
            with httpx.Client() as client:
                # Get current price
                price_resp = client.get(
                    f"{self.base_url}/ticker/price",
                    params={"symbol": symbol},
                    timeout=5,
                )
                price_resp.raise_for_status()
                price_data = orjson.loads(price_resp.content)

                # Get 24h stats
                stats_resp = client.get(
                    f"{self.base_url}/ticker/24hr", params={"symbol": symbol}, timeout=5
                )
                stats_resp.raise_for_status()
                stats_data = orjson.loads(stats_resp.content)

            result = PriceData(
                symbol=symbol,
                price=float(price_data["price"]),
                timestamp=now,
                change_24h=float(stats_data["priceChangePercent"]),
            )

            # Cache result
            self._cache[cache_key] = (result, now)
            return result

        except Exception as e:
            logger.warning("Error fetching price for %s: %s", symbol, e)
            return None

    def get_btc_price(self) -> PriceData | None:
        """Get BTC/USDT price."""
        return self.get_price("BTCUSDT")

    def get_eth_price(self) -> PriceData | None:
        """Get ETH/USDT price."""
        return self.get_price("ETHUSDT")

    def get_multiple_prices(self, symbols: list) -> dict[str, PriceData]:
        """Get prices for multiple symbols."""
        results = {}
        for symbol in symbols:
            price_data = self.get_price(symbol)
            if price_data:
                results[symbol] = price_data
        return results
