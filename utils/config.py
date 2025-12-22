"""Configuration utilities."""

import os
from dataclasses import dataclass


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

    # Strategy settings
    price_threshold: float = 0.01  # 1% price move threshold
    market_lag_threshold: float = 0.005  # 0.5% lag threshold
    min_confidence: float = 0.6

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
            # Override defaults with env vars if present
            paper_trading=os.getenv("PAPER_TRADING", "true").lower() == "true",
            initial_balance=float(os.getenv("INITIAL_BALANCE", "10000")),
            max_position_size=float(os.getenv("MAX_POSITION_SIZE", "100")),
            price_threshold=float(os.getenv("PRICE_THRESHOLD", "0.01")),
            market_lag_threshold=float(os.getenv("MARKET_LAG_THRESHOLD", "0.005")),
            min_confidence=float(os.getenv("MIN_CONFIDENCE", "0.6")),
            price_update_interval=int(os.getenv("PRICE_UPDATE_INTERVAL", "30")),
            cache_ttl=int(os.getenv("CACHE_TTL", "10")),
            # Monitoring settings
            sentry_dsn=os.getenv("SENTRY_DSN"),
            enable_performance_monitoring=os.getenv("ENABLE_PERFORMANCE_MONITORING", "true").lower() == "true",
            development=os.getenv("DEVELOPMENT", "true").lower() == "true",
        )

    def validate(self) -> bool:
        """Validate configuration."""
        if not all(
            [self.api_key, self.api_secret, self.api_passphrase, self.private_key]
        ):
            print("Missing required API credentials")
            return False

        if self.initial_balance <= 0:
            print("Initial balance must be positive")
            return False

        if not (0 < self.min_confidence <= 1):
            print("Min confidence must be between 0 and 1")
            return False

        return True
