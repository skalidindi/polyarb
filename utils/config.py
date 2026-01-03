"""Configuration utilities."""

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Config:
    """Application configuration."""

    # Polymarket settings
    polymarket_host: str = "https://clob.polymarket.com"
    polymarket_chain_id: int = 137

    # API credentials (loaded from environment)
    api_key: str | None = None
    api_secret: str | None = None
    api_passphrase: str | None = None
    private_key: str | None = None

    # Trading settings
    paper_trading: bool = True
    initial_balance: float = 10000.0
    max_position_size: float = 100.0
    execution_mode: str = "buy_both_only"  # Phase 2: "buy_both_only", Phase 3: "full"

    # Risk management
    daily_loss_limit: float = 100.0  # Stop trading if daily loss exceeds
    max_open_positions: int = 10  # Maximum concurrent positions

    # Fees and costs
    polymarket_fee_rate: float = 0.0  # 0% fees as of 2025 (was 2% historically)
    estimated_gas_cost: float = 0.50  # Estimated cost per blockchain transaction
    min_profit_threshold: float = (
        0.01  # Minimum profit required (lowered due to 0% fees)
    )

    # Strategy settings
    price_threshold: float = 0.01  # 1% price move threshold
    market_lag_threshold: float = 0.005  # 0.5% lag threshold
    min_confidence: float = 0.8  # Raised from 0.6
    max_price_sum_deviation: float = 0.05  # 5% deviation from $1
    min_liquidity_depth: float = 100.0  # Minimum orderbook depth

    # Data feed settings
    price_update_interval: int = 30  # seconds
    cache_ttl: int = 10  # seconds

    # Monitoring settings
    sentry_dsn: str | None = None
    enable_performance_monitoring: bool = True
    development: bool = True  # Set to False in production

    @classmethod
    def from_env(cls) -> "Config":
        """Create config from environment variables."""
        return cls(
            api_key=os.getenv("POLYMARKET_API_KEY"),
            api_secret=os.getenv("POLYMARKET_API_SECRET"),
            api_passphrase=os.getenv("POLYMARKET_API_PASSPHRASE"),
            private_key=os.getenv("POLYMARKET_PRIVATE_KEY"),
            # Trading settings
            paper_trading=os.getenv("PAPER_TRADING", "true").lower() == "true",
            initial_balance=float(os.getenv("INITIAL_BALANCE", "10000")),
            max_position_size=float(os.getenv("MAX_POSITION_SIZE", "100")),
            execution_mode=os.getenv("EXECUTION_MODE", "buy_both_only"),
            # Risk management
            daily_loss_limit=float(os.getenv("DAILY_LOSS_LIMIT", "100")),
            max_open_positions=int(os.getenv("MAX_OPEN_POSITIONS", "10")),
            # Fees and costs
            polymarket_fee_rate=float(os.getenv("POLYMARKET_FEE_RATE", "0.0")),
            estimated_gas_cost=float(os.getenv("ESTIMATED_GAS_COST", "0.50")),
            min_profit_threshold=float(os.getenv("MIN_PROFIT_THRESHOLD", "0.01")),
            # Strategy settings
            price_threshold=float(os.getenv("PRICE_THRESHOLD", "0.01")),
            market_lag_threshold=float(os.getenv("MARKET_LAG_THRESHOLD", "0.005")),
            min_confidence=float(os.getenv("MIN_CONFIDENCE", "0.8")),
            max_price_sum_deviation=float(os.getenv("MAX_PRICE_SUM_DEVIATION", "0.05")),
            min_liquidity_depth=float(os.getenv("MIN_LIQUIDITY_DEPTH", "100")),
            # Data feed settings
            price_update_interval=int(os.getenv("PRICE_UPDATE_INTERVAL", "30")),
            cache_ttl=int(os.getenv("CACHE_TTL", "10")),
            # Monitoring settings
            sentry_dsn=os.getenv("SENTRY_DSN"),
            enable_performance_monitoring=os.getenv(
                "ENABLE_PERFORMANCE_MONITORING", "true"
            ).lower()
            == "true",
            development=os.getenv("DEVELOPMENT", "true").lower() == "true",
        )

    def validate(self) -> bool:
        """Validate configuration."""
        if not all(
            [self.api_key, self.api_secret, self.api_passphrase, self.private_key]
        ):
            logger.error("Missing required API credentials")
            return False

        if self.initial_balance <= 0:
            logger.error("Initial balance must be positive")
            return False

        if not (0 < self.min_confidence <= 1):
            logger.error("Min confidence must be between 0 and 1")
            return False

        return True
