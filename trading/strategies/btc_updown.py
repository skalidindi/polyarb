"""Bitcoin 15-minute up/down arbitrage strategy.

Strategy from: https://x.com/carverfomo/status/2002317387975311799

When BTC price whipsaws, Polymarket odds lag the live feed and the book
briefly misprices both sides. This strategy catches when Up + Down < $1.00.
"""

import json
import logging
from typing import Any

from trading.strategies.base import (
    ArbitrageOpportunity,
    SignalType,
    StrategyBase,
    TradingSignal,
)

logger = logging.getLogger(__name__)


class BtcUpDownStrategy(StrategyBase):
    """Bitcoin 15-minute up/down arbitrage strategy."""

    def __init__(
        self,
        client: Any,
        min_profit_threshold: float = 0.01,  # Minimum 1¢ profit
        max_price_sum: float = 0.99,  # Buy when Up + Down < $0.99
    ) -> None:
        """Initialize strategy.

        Args:
            client: Polymarket client instance
            min_profit_threshold: Minimum profit to trigger signal (default: $0.01)
            max_price_sum: Maximum price sum to trigger buy (default: $0.99)
        """
        super().__init__("btc_updown")
        self.client = client
        self.min_profit_threshold = min_profit_threshold
        self.max_price_sum = max_price_sum

    def get_strategy_description(self) -> str:
        """Get strategy description."""
        return (
            f"Bitcoin 15m up/down arbitrage: Buy both when Up + Down < ${self.max_price_sum:.2f}, "
            f"min profit ${self.min_profit_threshold:.2f}"
        )

    def find_btc_markets(self) -> list[dict]:
        """Find active Bitcoin up/down markets.

        Returns:
            List of active BTC up/down market dictionaries
        """
        # Use client's get_gamma_events method
        breakpoint()
        try:
            events = self.client.get_gamma_events(
                tag_id="102175",  # Bitcoin tag
                exclude_tag_ids=["39", "101267", "818"],  # Exclude certain types
                closed=False,
                limit=500,
            )
        except Exception as e:
            logger.error("Error fetching Bitcoin events: %s", e)
            return []

        # Extract markets from events
        btc_markets = []
        for event in events:
            markets = event.get("markets", [])
            for market in markets:
                accepting = market.get("acceptingOrders", False)
                if accepting:
                    btc_markets.append(market)

        return btc_markets

    def analyze(self, market_data: dict) -> list[TradingSignal]:
        """Analyze a Bitcoin up/down market for arbitrage.

        Args:
            market_data: Market data from Gamma API

        Returns:
            List of trading signals (empty if no opportunity)
        """
        question = market_data.get("question", "")
        accepting_orders = market_data.get("acceptingOrders", False)

        if not accepting_orders:
            return []

        # Parse outcomes to verify binary market
        outcomes_raw = market_data.get("outcomes", "[]")
        if isinstance(outcomes_raw, str):
            try:
                outcomes = json.loads(outcomes_raw)
            except json.JSONDecodeError:
                return []
        else:
            outcomes = outcomes_raw

        # Need exactly 2 outcomes (Up and Down)
        if len(outcomes) != 2:
            return []

        # Parse token IDs
        clob_token_ids_raw = market_data.get("clobTokenIds", "[]")
        if isinstance(clob_token_ids_raw, str):
            try:
                clob_token_ids = json.loads(clob_token_ids_raw)
            except json.JSONDecodeError:
                return []
        else:
            clob_token_ids = clob_token_ids_raw

        # Need exactly 2 token IDs
        if len(clob_token_ids) != 2:
            return []

        up_token_id = clob_token_ids[0]
        down_token_id = clob_token_ids[1]

        # Get orderbooks
        try:
            clob_client = self.client._get_client()
            up_book = clob_client.get_order_book(up_token_id)
            down_book = clob_client.get_order_book(down_token_id)

            if not up_book.asks or not down_book.asks:
                return []

            up_ask = float(up_book.asks[0].price)
            down_ask = float(down_book.asks[0].price)
            price_sum = up_ask + down_ask

            # Check for arbitrage opportunity
            if price_sum < self.max_price_sum:
                profit = 1.00 - price_sum

                if profit >= self.min_profit_threshold:
                    # Create arbitrage opportunity
                    opportunity = ArbitrageOpportunity(
                        market_id=market_data.get("conditionId", ""),
                        market_question=question,
                        yes_token_id=up_token_id,
                        no_token_id=down_token_id,
                        yes_price=up_ask,
                        no_price=down_ask,
                        price_sum=price_sum,
                        opportunity_type="buy_both",
                        profit_potential=profit,
                        confidence=0.95,  # High confidence for structural arbitrage
                    )

                    signal = TradingSignal(
                        signal_type=SignalType.ARBITRAGE,
                        confidence=0.95,
                        reason=f"BTC up/down arbitrage: Up + Down = ${price_sum:.4f} < $1.00 (profit: ${profit:.4f})",
                        market_id=market_data.get("conditionId"),
                        metadata={
                            "opportunity": opportunity,
                            "price_sum": price_sum,
                            "max_threshold": self.max_price_sum,
                        },
                    )

                    return [signal]

        except Exception as e:
            logger.debug("Skipping market %s due to orderbook error: %s", question, e)

        return []

    def scan_all_markets(self) -> list[TradingSignal]:
        """Scan all active Bitcoin up/down markets.

        Returns:
            List of trading signals for all opportunities found
        """
        btc_markets = self.find_btc_markets()
        logger.info("Found %d Bitcoin up/down markets to analyze", len(btc_markets))

        all_signals = []

        for i, market in enumerate(btc_markets):
            question = market.get("question", "Unknown")
            logger.debug(
                "  [%d/%d] Checking: %s...", i + 1, len(btc_markets), question[:60]
            )
            signals = self.analyze(market)
            if signals:
                logger.info("    ⚡ FOUND ARBITRAGE: %s", question[:60])
            all_signals.extend(signals)

        return all_signals
