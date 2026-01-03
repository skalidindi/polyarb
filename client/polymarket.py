"""Polymarket client wrapper."""

import logging
import os

import requests
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, AssetType, BalanceAllowanceParams

logger = logging.getLogger(__name__)


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

    def get_balance(self) -> float:
        """Get USDC collateral balance."""
        client = self._get_client()
        params = BalanceAllowanceParams(asset_type=AssetType.CONDITIONAL)  # type: ignore[attr-defined]
        balance_info = client.get_balance_allowance(params)
        return float(balance_info.get("balance", 0))

    def get_token_balance(self, token_id: str) -> float:
        """Get balance for a specific conditional token.

        Args:
            token_id: The conditional token ID to check balance for

        Returns:
            Token balance as float
        """
        client = self._get_client()
        params = BalanceAllowanceParams(
            asset_type=AssetType.CONDITIONAL,  # type: ignore[attr-defined]
            token_id=token_id,
        )
        balance_info = client.get_balance_allowance(params)
        return float(balance_info.get("balance", 0))

    def get_token_price(self, token_id: str) -> float | None:
        """Get current market price for a token."""
        try:
            return self.get_midpoint(token_id)
        except Exception as e:
            logger.warning("Error fetching price for token %s: %s", token_id, e)
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

    def get_gamma_markets(
        self,
        limit: int = 100,
        offset: int = 0,
        closed: bool = False,
        liquidity_num_min: float | None = None,
        volume_num_min: float | None = None,
        order: str | None = None,
        ascending: bool = False,
    ) -> list[dict]:
        """Get markets from Gamma Markets API with filtering.

        Args:
            limit: Number of markets to return (default: 100)
            offset: Offset for pagination (default: 0)
            closed: Filter by closed status (default: False for open markets)
            liquidity_num_min: Minimum liquidity threshold
            volume_num_min: Minimum volume threshold
            order: Field to order by (e.g., "liquidity_num", "volume_num")
            ascending: Sort direction (default: False for descending)

        Returns:
            List of market dictionaries
        """
        url = "https://gamma-api.polymarket.com/markets"
        params: dict[str, str | int | float | bool] = {
            "limit": limit,
            "offset": offset,
            "closed": closed,
            "ascending": ascending,
        }

        if liquidity_num_min is not None:
            params["liquidity_num_min"] = liquidity_num_min
        if volume_num_min is not None:
            params["volume_num_min"] = volume_num_min
        if order is not None:
            params["order"] = order

        response = requests.get(url, params=params, timeout=30)
        if not response.ok:
            logger.error("Error response: %s - %s", response.status_code, response.text)
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]

    def get_gamma_events(
        self,
        tag_id: str | None = None,
        exclude_tag_ids: list[str] | None = None,
        closed: bool = False,
        limit: int = 100,
    ) -> list[dict]:
        """Get events from Gamma Events API with filtering.

        Args:
            tag_id: Tag ID to filter by (e.g., "102175" for Bitcoin)
            exclude_tag_ids: List of tag IDs to exclude
            closed: Filter by closed status (default: False for open events)
            limit: Number of events to return (default: 100)

        Returns:
            List of event dictionaries with nested markets
        """
        url = "https://gamma-api.polymarket.com/events"

        # Build params as list of tuples to support multiple exclude_tag_id values
        params: list[tuple[str, str | int]] = [
            ("closed", "true" if closed else "false"),
            ("limit", limit),
        ]

        if tag_id is not None:
            params.append(("tag_id", tag_id))

        # Add multiple exclude_tag_id parameters
        if exclude_tag_ids:
            for tag in exclude_tag_ids:
                params.append(("exclude_tag_id", tag))

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]
