# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Commands

### Running the Bot
```bash
uv run start                # Start the arbitrage bot (preferred)
uv run main.py              # Alternative start command
```

### Development Commands
```bash
uv add <package>            # Add new dependency
uv add --dev <package>      # Add development dependency
uv run ruff check .         # Lint codebase
uv run ruff format .        # Format code
uv run mypy . --explicit-package-bases  # Type checking
uv run pytest              # Run all tests
uv run pytest -n auto      # Run tests in parallel
uv run pytest -m trading   # Run only trading strategy tests
```

### Environment Setup
The bot requires Polymarket API credentials in a `.env` file:
```bash
cp .env.example .env
# Edit .env with your actual API keys
```

## Architecture Overview

### Core Strategy Pattern
The bot implements a pluggable strategy architecture centered around arbitrage detection:

- **StrategyBase**: Abstract base class defining the strategy interface with `analyze()` method
- **TradingSignal**: Data class containing signal metadata and confidence scores
- **ArbitrageOpportunity**: Specific opportunity details for market rebalancing arbitrage

### Key Components

**Client Layer (`client/`)**
- `PolymarketClient`: Wrapper around `py-clob-client` providing simplified market data access
- Handles authentication, price fetching, and API error handling

**Strategy Engine (`trading/strategies/`)**
- `MarketRebalancingStrategy`: Detects when YES + NO token prices ≠ $1.00
- `SimpleArbitrageStrategy`: Legacy crypto price movement strategy
- All strategies implement `StrategyBase` for consistent interface

**Data Pipeline (`data/`)**
- `CryptoPriceFeed`: Binance API integration with caching
- `PriceData`: Standardized price data container

**Configuration (`utils/`)**
- `Config`: Environment-based configuration with validation
- All settings configurable via environment variables with sensible defaults

### Trading Flow

1. **Initialization**: `main.py` loads config, validates credentials, initializes client and strategy
2. **Market Scanning**: Fetches all available markets from Polymarket CLOB API
3. **Strategy Analysis**: Each market runs through `MarketRebalancingStrategy.analyze()`
4. **Opportunity Detection**: Strategy returns `TradingSignal` objects for profitable opportunities
5. **Paper Trading**: `PaperTrader` simulates trades and tracks P&L

### Modern Python Usage

The codebase uses Python 3.13+ features:
- Modern type hints (`dict`, `list`, `str | None` instead of `typing` imports)
- Dataclasses for data structures
- Enum classes for constants

### Testing Framework

The project uses a comprehensive testing stack optimized for trading strategy validation:

**Property-Based Testing with Hypothesis**:
- Tests trading logic across thousands of random price combinations
- Automatically finds edge cases that could cause losses
- `.hypothesis/` directory stores test results locally (not committed to git)
- Configuration in `pyproject.toml` ensures consistent behavior

**Test Categories**:
- `@pytest.mark.unit` - Fast unit tests
- `@pytest.mark.integration` - API integration tests  
- `@pytest.mark.trading` - Trading strategy tests
- `@pytest.mark.slow` - Long-running tests

**Parallel Execution**:
- Tests run in parallel using `pytest-xdist` for speed
- 16 workers automatically allocated based on CPU cores

### Key Configuration Points

**Strategy Tuning** (in `MarketRebalancingStrategy.__init__()`):
- `min_profit_threshold`: Minimum profit required (default 1¢)
- `min_confidence`: Confidence threshold for trade signals (default 0.8)
- `max_price_sum_deviation`: Maximum allowed price deviation from $1.00

**API Integration** (in `Config`):
- Requires Polymarket API credentials (key, secret, passphrase, private_key)
- Connects to Polygon mainnet (chain_id=137)
- Default paper trading mode for safety

### Error Handling

The bot gracefully handles:
- Missing orderbook data (returns `None` prices)
- API rate limits and 404 errors
- Invalid market structures (skips markets without YES/NO tokens)

### Strategy Development

To add new strategies:
1. Inherit from `StrategyBase`
2. Implement `analyze(market_data: dict) -> list[TradingSignal]`
3. Add to `trading/strategies/__init__.py` imports
4. Initialize in `main.py` alongside existing strategies