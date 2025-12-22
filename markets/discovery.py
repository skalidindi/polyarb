"""Market discovery and filtering utilities."""

import re
from typing import Any


class MarketDiscovery:
    """Discover and filter relevant markets for trading."""

    def __init__(self, client: Any) -> None:
        self.client = client

    def find_crypto_15min_markets(self) -> list[dict]:
        """Find 15-minute crypto up/down markets."""
        all_markets = []
        next_cursor = None

        # Fetch all markets (with pagination)
        while True:
            response = self.client.get_markets(next_cursor)
            markets = response.get("data", [])
            all_markets.extend(markets)

            # Check if there's more data
            next_cursor = response.get("next_cursor")
            if not next_cursor:
                break

        # Filter for 15-minute crypto markets
        crypto_15min_markets = []

        for market in all_markets:
            question = market.get("question", "").lower()
            description = market.get("description", "").lower()

            # Look for 15-minute timeframe
            time_match = self._contains_15min_timeframe(question, description)

            # Look for crypto symbols
            crypto_match = self._contains_crypto_symbols(question, description)

            # Look for up/down direction
            direction_match = self._contains_direction_terms(question, description)

            if time_match and crypto_match and direction_match:
                market["crypto_symbol"] = crypto_match
                market["direction"] = direction_match
                market["timeframe"] = time_match
                crypto_15min_markets.append(market)

        return crypto_15min_markets

    def _contains_15min_timeframe(self, question: str, description: str) -> str | None:
        """Check if text contains 15-minute timeframe references."""
        patterns = [
            r"15\s*min",
            r"15\s*minute",
            r"quarter\s*hour",
            r"0:15",
            r"fifteen\s*min",
        ]

        text = f"{question} {description}"
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return "15min"

        return None

    def _contains_crypto_symbols(self, question: str, description: str) -> str | None:
        """Check if text contains crypto symbols."""
        crypto_symbols = [
            "btc",
            "bitcoin",
            "eth",
            "ethereum",
            "sol",
            "solana",
            "ada",
            "cardano",
            "dot",
            "polkadot",
            "avax",
            "avalanche",
            "link",
            "chainlink",
            "matic",
            "polygon",
            "doge",
            "dogecoin",
            "xrp",
            "ripple",
        ]

        text = f"{question} {description}".lower()

        for symbol in crypto_symbols:
            if symbol in text:
                # Return standardized symbol
                if symbol in ["btc", "bitcoin"]:
                    return "BTC"
                elif symbol in ["eth", "ethereum"]:
                    return "ETH"
                elif symbol in ["sol", "solana"]:
                    return "SOL"
                # Add more mappings as needed
                else:
                    return symbol.upper()

        return None

    def _contains_direction_terms(self, question: str, description: str) -> str | None:
        """Check if text contains directional terms."""
        up_terms = ["up", "increase", "rise", "gain", "higher", "above", "pump"]
        down_terms = ["down", "decrease", "fall", "drop", "lower", "below", "dump"]

        text = f"{question} {description}".lower()

        has_up = any(term in text for term in up_terms)
        has_down = any(term in text for term in down_terms)

        if has_up and not has_down:
            return "up"
        elif has_down and not has_up:
            return "down"
        elif has_up and has_down:
            return "both"  # Market might be asking about direction

        return None

    def get_market_details(self, market_id: str) -> dict | None:
        """Get detailed information about a specific market."""
        # This would need to be implemented based on the API
        # For now, return basic info from the market list
        markets = self.find_crypto_15min_markets()
        return next((m for m in markets if m.get("condition_id") == market_id), None)

    def filter_active_markets(self, markets: list[dict]) -> list[dict]:
        """Filter for active (not expired) markets."""
        active_markets = []

        for market in markets:
            # Check if market is still active
            # This depends on the market data structure
            end_date = market.get("end_date_iso")
            if end_date:
                # Add logic to check if market hasn't expired
                # For now, assume all markets are active
                pass

            active_markets.append(market)

        return active_markets

    def get_top_volume_markets(
        self, markets: list[dict], limit: int = 10
    ) -> list[dict]:
        """Get markets with highest volume/liquidity."""
        # Sort by volume if available
        volume_markets = []

        for market in markets:
            volume = market.get("volume", 0)
            if volume > 0:
                volume_markets.append(market)

        # Sort by volume descending
        volume_markets.sort(key=lambda x: x.get("volume", 0), reverse=True)

        return volume_markets[:limit]
