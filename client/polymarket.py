"""Polymarket client wrapper."""

import os

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds


class PolymarketClient:
    """Wrapper around py-clob-client with convenience methods."""

    def __init__(self, host: str = "https://clob.polymarket.com", chain_id: int = 137):
        self.host = host
        self.chain_id = chain_id
        self._client = None

    def _get_client(self) -> ClobClient:
        """Initialize client with credentials."""
        if self._client is None:
            creds = ApiCreds(
                api_key=os.environ["POLYMARKET_API_KEY"],
                api_secret=os.environ["POLYMARKET_API_SECRET"],
                api_passphrase=os.environ["POLYMARKET_API_PASSPHRASE"],
            )
            self._client = ClobClient(
                self.host,
                key=os.environ["POLYMARKET_PRIVATE_KEY"],
                chain_id=self.chain_id,
                creds=creds,
            )
        return self._client

    def get_markets(self, next_cursor: str | None = None) -> dict:
        """Get available markets."""
        client = self._get_client()
        if next_cursor:
            return client.get_markets(next_cursor=next_cursor)  # type: ignore[no-any-return]
        return client.get_markets()  # type: ignore[no-any-return]

    def get_orderbook(self, token_id: str) -> dict:
        """Get orderbook for a specific token."""
        client = self._get_client()
        return client.get_orderbook(token_id)  # type: ignore[no-any-return]

    def get_midpoint(self, token_id: str) -> float:
        """Get midpoint price for a token."""
        client = self._get_client()
        return client.get_midpoint(token_id)  # type: ignore[no-any-return]

    def get_balance(self, token_type: str = "USDC") -> float:
        """Get balance for specified token type."""
        client = self._get_client()
        balance_info = client.get_balance(token_type)
        return float(balance_info.get("balance", 0))

    def get_token_price(self, token_id: str) -> float | None:
        """Get current market price for a token."""
        try:
            return self.get_midpoint(token_id)
        except Exception as e:
            print(f"Error fetching price for token {token_id}: {e}")
            return None

    def get_market_prices(self, market_data: dict) -> dict[str, float | None]:
        """Get prices for YES and NO tokens in a market."""
        tokens = market_data.get("tokens", [])
        prices = {}

        for token in tokens:
            token_id = token.get("token_id")
            outcome = token.get("outcome", "").lower()

            if token_id and outcome in ["yes", "no"]:
                price = self.get_token_price(token_id)
                prices[outcome] = price

        return prices
