# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Documentation

**Polymarket API Documentation**: https://docs.polymarket.com/llms-full.txt
- Complete API reference for CLOB, orders, markets, and trading mechanics
- **Critical**: As of 2025, Polymarket has **0% fees** across all volume levels
- Collateral token: **USDC.e** (Bridged USDC from Ethereum) on Polygon
- Order types: GTC, GTD, FOK (Fill-Or-Kill), FAK (Fill-And-Kill)
- Rate limits: 500 POST /order per 10s (burst), 50 GET /book per 10s
- Batch orders: Up to 15 orders per request

## Essential Commands

### Running the Bot
```bash
uv run start                # Start the arbitrage bot (preferred)
uv run polyarb              # Alternative command
uv run python main.py       # Direct python invocation
```

**Logging:** All runs automatically create timestamped log files in `logs/polyarb_YYYYMMDD_HHMMSS.log`

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

### Arbitrage Execution Flow

**Scenario A: YES + NO < $1.00 (Underpriced)**
- Strategy: Buy both YES and NO tokens
- Execution: Place two BUY orders → CLOB auto-mints via `splitPosition()`
- No blockchain operations needed (CLOB handles minting)

**Scenario B: YES + NO > $1.00 (Overpriced)**
- Strategy: Sell both YES and NO tokens
- Execution:
  1. Split $X USDC → X YES + X NO tokens (blockchain tx)
  2. Place two SELL orders → CLOB burns tokens via `mergePositions()`
- Requires Web3 operations (gas cost ~$0.50)

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
- `min_profit_threshold`: Minimum profit required (default 1¢, lowered due to 0% fees)
- `min_confidence`: Confidence threshold for trade signals (default 0.8)
- `max_price_sum_deviation`: Maximum allowed price deviation from $1.00
- `polymarket_fee_rate`: Currently 0% (was 2% historically)

**API Integration** (in `Config`):
- Requires Polymarket API credentials (key, secret, passphrase, private_key)
- Connects to Polygon mainnet (chain_id=137)
- Collateral: USDC.e (Bridged USDC) - address: 0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174
- Default paper trading mode for safety

### API Rate Limits & Best Practices

**Rate Limits** (as of May 2025):
- POST /order: 500 req/10s (burst), 3000 req/10min (sustained)
- GET /book: 50 req/10s for API access (300 req/10s for website)
- GET /price: 100 req/10s

**Best Practices**:
- Use batch order API (up to 15 orders per request) for atomic execution
- Prefer FOK (Fill-Or-Kill) order type for arbitrage to ensure complete sets
- Cache aggressively to avoid hitting rate limits
- Use WebSocket (RTDS) for real-time data instead of polling (Phase 4)

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