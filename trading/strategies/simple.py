"""Trading strategies for paper trading."""

from dataclasses import dataclass

from data.feeds import PriceData


@dataclass
class TradeSignal:
    """Trading signal container."""

    should_trade: bool
    side: str  # "buy" or "sell"
    confidence: float  # 0-1
    reason: str
    target_price: float | None = None


class SimpleArbitrageStrategy:
    """Simple arbitrage strategy based on crypto price movements."""

    def __init__(
        self,
        price_threshold: float = 0.01,  # 1% price move threshold
        market_lag_threshold: float = 0.005,  # 0.5% lag threshold
        min_confidence: float = 0.6,
    ):
        self.price_threshold = price_threshold
        self.market_lag_threshold = market_lag_threshold
        self.min_confidence = min_confidence
        self._last_crypto_price: float | None = None

    def analyze_signal(
        self, crypto_price: PriceData, market_price: float, market_question: str
    ) -> TradeSignal:
        """Analyze if there's a trading opportunity."""

        # Check if we have previous price data
        if self._last_crypto_price is None:
            self._last_crypto_price = crypto_price.price
            return TradeSignal(
                should_trade=False,
                side="hold",
                confidence=0.0,
                reason="Insufficient price history",
            )

        # Calculate price change
        price_change = (
            crypto_price.price - self._last_crypto_price
        ) / self._last_crypto_price
        self._last_crypto_price = crypto_price.price

        # Determine if this is an "up" or "down" market
        is_up_market = (
            "up" in market_question.lower() or "increase" in market_question.lower()
        )
        is_down_market = (
            "down" in market_question.lower() or "decrease" in market_question.lower()
        )

        if not (is_up_market or is_down_market):
            return TradeSignal(
                should_trade=False,
                side="hold",
                confidence=0.0,
                reason="Cannot determine market direction from question",
            )

        # Check for significant price movement
        if abs(price_change) < self.price_threshold:
            return TradeSignal(
                should_trade=False,
                side="hold",
                confidence=0.0,
                reason=f"Price change {price_change:.2%} below threshold {self.price_threshold:.2%}",
            )

        # Analyze arbitrage opportunity
        if is_up_market and price_change > 0:
            # Crypto went up, should "YES" tokens be higher?
            expected_price = min(0.9, market_price + abs(price_change) * 0.5)
            if expected_price - market_price > self.market_lag_threshold:
                confidence = min(1.0, abs(price_change) / self.price_threshold)
                return TradeSignal(
                    should_trade=confidence >= self.min_confidence,
                    side="buy",
                    confidence=confidence,
                    reason=f"Crypto up {price_change:.2%}, market lagging",
                    target_price=expected_price,
                )

        elif is_down_market and price_change < 0:
            # Crypto went down, should "YES" tokens be higher?
            expected_price = min(0.9, market_price + abs(price_change) * 0.5)
            if expected_price - market_price > self.market_lag_threshold:
                confidence = min(1.0, abs(price_change) / self.price_threshold)
                return TradeSignal(
                    should_trade=confidence >= self.min_confidence,
                    side="buy",
                    confidence=confidence,
                    reason=f"Crypto down {price_change:.2%}, market lagging",
                    target_price=expected_price,
                )

        elif is_up_market and price_change < 0:
            # Crypto went down but market thinks it will go up - fade the market
            expected_price = max(0.1, market_price - abs(price_change) * 0.3)
            if market_price - expected_price > self.market_lag_threshold:
                confidence = min(
                    1.0, abs(price_change) / self.price_threshold * 0.7
                )  # Lower confidence for fading
                return TradeSignal(
                    should_trade=confidence >= self.min_confidence,
                    side="sell",
                    confidence=confidence,
                    reason=f"Crypto down {price_change:.2%}, fading up market",
                    target_price=expected_price,
                )

        elif is_down_market and price_change > 0:
            # Crypto went up but market thinks it will go down - fade the market
            expected_price = max(0.1, market_price - abs(price_change) * 0.3)
            if market_price - expected_price > self.market_lag_threshold:
                confidence = min(
                    1.0, abs(price_change) / self.price_threshold * 0.7
                )  # Lower confidence for fading
                return TradeSignal(
                    should_trade=confidence >= self.min_confidence,
                    side="sell",
                    confidence=confidence,
                    reason=f"Crypto up {price_change:.2%}, fading down market",
                    target_price=expected_price,
                )

        return TradeSignal(
            should_trade=False,
            side="hold",
            confidence=0.0,
            reason="No clear arbitrage opportunity",
        )
