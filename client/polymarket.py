"""Polymarket client wrapper."""

import logging
import os
from typing import Any

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
            # Check if we need to generate credentials
            if not all(
                [
                    os.getenv("POLYMARKET_API_KEY"),
                    os.getenv("POLYMARKET_API_SECRET"),
                    os.getenv("POLYMARKET_API_PASSPHRASE"),
                ]
            ):
                logger.warning(
                    "⚠️  API credentials missing! Generating from private key..."
                )
                logger.warning(
                    "💡 Save these to .env to avoid regenerating on every run"
                )
                self.create_api_credentials()

            # Get funder address - use env var if provided, otherwise derive from key
            private_key = os.environ["POLYMARKET_PRIVATE_KEY"]

            if os.getenv("POLYMARKET_FUNDER"):
                # Proxy wallet setup (Magic/email): funder is separate from signing key
                funder = os.environ["POLYMARKET_FUNDER"]
                signature_type = 1  # Proxy wallet signature type
            else:
                # EOA wallet: derive funder address from private key
                from eth_account import Account

                account = Account.from_key(private_key)
                funder = account.address
                signature_type = 0  # EOA signature type

            creds = ApiCreds(
                api_key=os.environ["POLYMARKET_API_KEY"],
                api_secret=os.environ["POLYMARKET_API_SECRET"],
                api_passphrase=os.environ["POLYMARKET_API_PASSPHRASE"],
            )
            self._client = ClobClient(
                self.host,
                key=private_key,
                chain_id=self.chain_id,
                signature_type=signature_type,
                funder=funder,
                creds=creds,
            )
            self._client.set_api_creds(creds)
        return self._client

    def create_api_credentials(self) -> dict[str, str]:
        """Create or derive API credentials from private key.

        This generates API credentials (key, secret, passphrase) from your wallet's
        private key. The credentials are automatically stored in environment variables
        for the current session.

        You should save these to your .env file for future use.

        Returns:
            Dictionary with 'api_key', 'api_secret', and 'api_passphrase'

        Raises:
            KeyError: If POLYMARKET_PRIVATE_KEY is not set
            Exception: If credential generation fails
        """
        private_key = os.environ["POLYMARKET_PRIVATE_KEY"]

        logger.info("Generating API credentials from private key...")

        # Create temporary client without creds to generate them
        temp_client = ClobClient(
            host=self.host,
            key=private_key,
            chain_id=self.chain_id,
        )

        # Generate or retrieve existing credentials
        creds = temp_client.create_or_derive_api_creds()

        # Store in environment for this session
        os.environ["POLYMARKET_API_KEY"] = creds.api_key
        os.environ["POLYMARKET_API_SECRET"] = creds.api_secret
        os.environ["POLYMARKET_API_PASSPHRASE"] = creds.api_passphrase

        logger.info("✅ API credentials generated successfully!")
        logger.warning(
            "Add these to your .env file:\n"
            f"POLYMARKET_API_KEY={creds.api_key}\n"
            f"POLYMARKET_API_SECRET={creds.api_secret}\n"
            f"POLYMARKET_API_PASSPHRASE={creds.api_passphrase}"
        )

        return {
            "api_key": creds.api_key,
            "api_secret": creds.api_secret,
            "api_passphrase": creds.api_passphrase,
        }

    def get_wallet_address(self) -> str:
        """Get the wallet address that holds funds (funder address).

        Returns:
            Ethereum address as hex string (0x...)
        """
        # Return funder address if set (proxy wallet), otherwise derive from key (EOA)
        if os.getenv("POLYMARKET_FUNDER"):
            return os.environ["POLYMARKET_FUNDER"]
        else:
            from eth_account import Account

            private_key = os.environ["POLYMARKET_PRIVATE_KEY"]
            account = Account.from_key(private_key)
            return account.address

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
        params = BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)  # type: ignore[attr-defined]
        balance_info: Any = client.get_balance_allowance(params)
        # Balance is returned as string in wei format (6 decimals for USDC.e)
        balance_wei = float(balance_info.get("balance", 0))
        return balance_wei / 1_000_000  # Convert from wei to USDC

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
        balance_info: Any = client.get_balance_allowance(params)
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
