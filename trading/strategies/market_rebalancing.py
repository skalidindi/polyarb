"""Market rebalancing arbitrage strategy."""

import logging
import time
from typing import Any

from .base import ArbitrageOpportunity, SignalType, StrategyBase, TradingSignal


class MarketRebalancingStrategy(StrategyBase):
    """
    Detects arbitrage opportunities where YES + NO token prices != $1.00

    This is the simplest form of arbitrage on prediction markets.
    When YES + NO prices deviate from $1, there's a risk-free profit opportunity.
    """

    def __init__(
        self,
        client: Any,
        min_profit_threshold: float = 0.01,  # Minimum $0.01 profit
        max_price_sum_deviation: float = 0.05,  # 5% deviation from $1
        min_confidence: float = 0.8,
    ) -> None:
        super().__init__("Market Rebalancing Arbitrage")
        self.client = client
        self.min_profit_threshold = min_profit_threshold
        self.max_price_sum_deviation = max_price_sum_deviation
        self.min_confidence = min_confidence
        self.logger = logging.getLogger(f"polyarb.{self.__class__.__name__}")

    def analyze(self, market_data: dict) -> list[TradingSignal]:
        """Analyze market for rebalancing arbitrage opportunities."""
        if not self.enabled:
            return []

        signals: list[TradingSignal] = []

        # Extract market information
        market_id = market_data.get("condition_id")
        market_question = market_data.get("question", "Unknown")
        tokens = market_data.get("tokens", [])

        if len(tokens) < 2:
            return signals

        # Find YES and NO tokens
        yes_token = next((t for t in tokens if t.get("outcome") == "Yes"), None)
        no_token = next((t for t in tokens if t.get("outcome") == "No"), None)

        if not yes_token or not no_token:
            return signals

        # Get current prices
        yes_price = self.client.get_token_price(yes_token.get("token_id"))
        no_price = self.client.get_token_price(no_token.get("token_id"))

        if yes_price is None or no_price is None:
            return signals

        # Check for arbitrage opportunity
        if market_id is None:
            return signals
        
        opportunity = self._detect_arbitrage(
            market_id=market_id,
            market_question=market_question,
            yes_token_id=yes_token.get("token_id"),
            no_token_id=no_token.get("token_id"),
            yes_price=yes_price,
            no_price=no_price,
        )

        if opportunity:
            self.opportunities_found += 1
            signal = self._create_signal_from_opportunity(opportunity)
            signals.append(signal)

        return signals

    def _detect_arbitrage(
        self,
        market_id: str,
        market_question: str,
        yes_token_id: str,
        no_token_id: str,
        yes_price: float,
        no_price: float,
    ) -> ArbitrageOpportunity | None:
        """Detect if there's an arbitrage opportunity."""

        price_sum = yes_price + no_price
        deviation = abs(price_sum - 1.0)

        # Check if deviation exceeds threshold
        if deviation < self.min_profit_threshold:
            return None

        # Calculate profit potential
        if price_sum < 1.0:
            # Both tokens are underpriced - buy both
            profit_potential = 1.0 - price_sum
            opportunity_type = "buy_both"
        else:
            # Both tokens are overpriced - sell both (short)
            profit_potential = price_sum - 1.0
            opportunity_type = "sell_both"

        # Calculate confidence based on deviation size
        confidence = min(1.0, deviation / self.max_price_sum_deviation)

        if confidence < self.min_confidence:
            return None

        return ArbitrageOpportunity(
            market_id=market_id,
            market_question=market_question,
            yes_token_id=yes_token_id,
            no_token_id=no_token_id,
            yes_price=yes_price,
            no_price=no_price,
            price_sum=price_sum,
            profit_potential=profit_potential,
            confidence=confidence,
            opportunity_type=opportunity_type,
        )

    def _create_signal_from_opportunity(
        self, opportunity: ArbitrageOpportunity
    ) -> TradingSignal:
        """Create trading signal from arbitrage opportunity."""

        if opportunity.opportunity_type == "buy_both":
            reason = f"Price sum {opportunity.price_sum:.3f} < $1.00, profit: ${opportunity.profit_potential:.3f}"
        else:
            reason = f"Price sum {opportunity.price_sum:.3f} > $1.00, profit: ${opportunity.profit_potential:.3f}"

        return TradingSignal(
            signal_type=SignalType.ARBITRAGE,  # Special arbitrage signal
            confidence=opportunity.confidence,
            reason=reason,
            market_id=opportunity.market_id,
            metadata={
                "opportunity": opportunity,
                "strategy": self.name,
                "timestamp": time.time(),
            },
        )

    def _get_token_price(self, token_id: str) -> float | None:
        """Get current price for a token."""
        return self.client.get_token_price(token_id)  # type: ignore[no-any-return]

    def get_strategy_description(self) -> str:
        """Return strategy description."""
        return (
            "Market Rebalancing Arbitrage: Detects opportunities where "
            "YES + NO token prices deviate from $1.00, indicating "
            "risk-free arbitrage profits."
        )
