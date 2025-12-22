"""Base class for trading strategies."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class SignalType(Enum):
    """Types of trading signals."""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    ARBITRAGE = "arbitrage"


@dataclass
class TradingSignal:
    """Trading signal with metadata."""

    signal_type: SignalType
    confidence: float  # 0-1
    reason: str
    market_id: str | None = None
    target_price: float | None = None
    size: float | None = None
    metadata: dict | None = None


@dataclass
class ArbitrageOpportunity:
    """Arbitrage opportunity details."""

    market_id: str
    market_question: str
    yes_token_id: str
    no_token_id: str
    yes_price: float
    no_price: float
    price_sum: float
    profit_potential: float
    confidence: float
    opportunity_type: str


class StrategyBase(ABC):
    """Base class for all trading strategies."""

    def __init__(self, name: str):
        self.name = name
        self.enabled = True
        self.opportunities_found = 0

    @abstractmethod
    def analyze(self, market_data: dict) -> list[TradingSignal]:
        """Analyze market data and return trading signals."""
        pass

    @abstractmethod
    def get_strategy_description(self) -> str:
        """Return a description of the strategy."""
        pass

    def enable(self) -> None:
        """Enable the strategy."""
        self.enabled = True

    def disable(self) -> None:
        """Disable the strategy."""
        self.enabled = False

    def get_stats(self) -> dict:
        """Get strategy statistics."""
        return {
            "name": self.name,
            "enabled": self.enabled,
            "opportunities_found": self.opportunities_found,
        }
