"""Main entry point for the polyarb trading bot."""

from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from client import PolymarketClient
from trading import BtcUpDownStrategy, PaperTrader
from utils import Config, setup_logging

# Load environment variables
load_dotenv()


def main() -> None:
    """Main application entry point."""
    # Setup configuration and logging
    config = Config.from_env()

    # Create logs directory and log file with timestamp
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"polyarb_{timestamp}.log"

    logger = setup_logging(level="INFO", log_file=str(log_file))
    logger.info(f"Logging to file: {log_file}")

    if not config.validate():
        logger.error("Configuration validation failed")
        return

    logger.info("Starting polyarb trading bot...")

    # Initialize components
    client = PolymarketClient(config.polymarket_host, config.polymarket_chain_id)
    paper_trader = PaperTrader(config.initial_balance)

    # Initialize Bitcoin 15m up/down strategy
    btc_strategy = BtcUpDownStrategy(
        client=client, min_profit_threshold=config.min_profit_threshold
    )

    logger.info("Scanning Bitcoin 15m up/down markets for arbitrage...")

    # Track opportunities by type
    opportunities_found = 0
    buy_both_count = 0

    # Scan all Bitcoin up/down markets
    signals = btc_strategy.scan_all_markets()

    logger.info(f"Found {len(signals)} arbitrage opportunities")

    for signal in signals:
        opportunities_found += 1
        buy_both_count += 1  # BTC strategy only does buy_both

        if signal.metadata is None:
            continue

        opportunity = signal.metadata["opportunity"]

        logger.info("🚨 ARBITRAGE OPPORTUNITY FOUND!")
        logger.info(f"   Market: {opportunity.market_name}")
        logger.info(f"   Up Price: ${opportunity.yes_price:.4f}")
        logger.info(f"   Down Price: ${opportunity.no_price:.4f}")
        logger.info(
            f"   Price Sum: ${signal.metadata['price_sum']:.4f} (threshold: ${signal.metadata['max_threshold']:.4f})"
        )
        logger.info(f"   Profit Potential: ${opportunity.profit_potential:.4f}")
        logger.info(f"   Confidence: {opportunity.confidence:.2%}")

        # In paper trading mode, simulate the trade
        if config.paper_trading:
            simulate_arbitrage_trade(paper_trader, opportunity, logger)

    logger.info(f"\n{'=' * 60}")
    logger.info("SCAN COMPLETE")
    logger.info(f"{'=' * 60}")
    logger.info(f"Total opportunities found: {opportunities_found}")
    logger.info(f"  - Buy Both (Up + Down < $1.00): {buy_both_count}")

    if opportunities_found > 0:
        logger.info(f"\n{'=' * 60}")
        logger.info("PAPER TRADING RESULTS")
        logger.info(f"{'=' * 60}")
        stats = paper_trader.get_stats()
        logger.info(f"Total trades: {stats['total_trades']}")
        logger.info(f"Total P&L: ${stats['total_pnl']:.2f}")
        logger.info(f"Win rate: {stats['win_rate']:.1f}%")
        logger.info(f"Current balance: ${stats['current_balance']:.2f}")
        logger.info(f"Total return: {stats['total_return']:.2f}%")
        paper_trader.save_to_file("arbitrage_trades.json")
        logger.info("\nTrade details saved to arbitrage_trades.json")


def simulate_arbitrage_trade(paper_trader: Any, opportunity: Any, logger: Any) -> None:
    """Simulate placing an arbitrage trade.

    Args:
        paper_trader: PaperTrader instance
        opportunity: ArbitrageOpportunity with market details
        logger: Logger instance
    """
    from trading.paper_trader import Side

    # Trade amount per arbitrage (equal amounts of YES and NO)
    trade_amount = 10.0

    try:
        if opportunity.opportunity_type == "buy_both":
            # Scenario A: YES + NO < $1.00 (Underpriced)
            # Just place BUY orders - CLOB automatically mints tokens
            logger.info("   📈 Scenario: BUY BOTH (underpriced market)")

            # Calculate token quantities needed
            yes_quantity = trade_amount / opportunity.yes_price
            no_quantity = trade_amount / opportunity.no_price

            # Place YES BUY order
            _yes_order = paper_trader.place_order(
                market_id=opportunity.market_id,
                market_question=opportunity.market_question,
                side=Side.BUY,
                size=yes_quantity,
                price=opportunity.yes_price,
                token_id=opportunity.yes_token_id,
            )

            # Place NO BUY order
            _no_order = paper_trader.place_order(
                market_id=opportunity.market_id,
                market_question=opportunity.market_question + " (NO)",
                side=Side.BUY,
                size=no_quantity,
                price=opportunity.no_price,
                token_id=opportunity.no_token_id,
            )

            total_cost = (yes_quantity * opportunity.yes_price) + (
                no_quantity * opportunity.no_price
            )
            expected_value = min(
                yes_quantity, no_quantity
            )  # Limited by smaller position
            raw_profit = expected_value - total_cost
            profit_after_fees = paper_trader.apply_fee(raw_profit)

            logger.info(
                f"   ✅ Bought {yes_quantity:.2f} YES @ ${opportunity.yes_price:.3f} + {no_quantity:.2f} NO @ ${opportunity.no_price:.3f}"
            )
            logger.info(
                f"   💰 Cost: ${total_cost:.3f} → Value: ${expected_value:.3f} → Raw Profit: ${raw_profit:.3f}"
            )
            if profit_after_fees != raw_profit:
                logger.info(f"   💸 After fees: ${profit_after_fees:.3f}")

        elif opportunity.opportunity_type == "sell_both":
            # Scenario B: YES + NO > $1.00 (Overpriced)
            # Must SPLIT USDC first to create tokens, then SELL them
            logger.info("   📉 Scenario: SELL BOTH (overpriced market)")

            # Step 1: Split USDC into YES + NO tokens
            split_amount = trade_amount
            split_success = paper_trader.split_usdc(
                amount=split_amount,
                yes_token_id=opportunity.yes_token_id,
                no_token_id=opportunity.no_token_id,
            )

            if not split_success:
                logger.error("   ❌ Insufficient balance to split USDC")
                return

            logger.info(f"   🔄 Split ${split_amount:.2f} USDC → tokens")

            # Step 2: Place SELL orders for both tokens
            # Sell the exact amount we created
            _yes_order = paper_trader.place_order(
                market_id=opportunity.market_id,
                market_question=opportunity.market_question,
                side=Side.SELL,
                size=split_amount,
                price=opportunity.yes_price,
                token_id=opportunity.yes_token_id,
            )

            _no_order = paper_trader.place_order(
                market_id=opportunity.market_id,
                market_question=opportunity.market_question + " (NO)",
                side=Side.SELL,
                size=split_amount,
                price=opportunity.no_price,
                token_id=opportunity.no_token_id,
            )

            total_proceeds = (split_amount * opportunity.yes_price) + (
                split_amount * opportunity.no_price
            )
            raw_profit = total_proceeds - split_amount
            profit_after_fees = paper_trader.apply_fee(raw_profit)
            # Note: Gas cost would be deducted here in real execution

            logger.info(
                f"   ✅ Sold {split_amount:.2f} YES @ ${opportunity.yes_price:.3f} + {split_amount:.2f} NO @ ${opportunity.no_price:.3f}"
            )
            logger.info(
                f"   💰 Cost: ${split_amount:.3f} → Proceeds: ${total_proceeds:.3f} → Raw Profit: ${raw_profit:.3f}"
            )
            if profit_after_fees != raw_profit:
                logger.info(f"   💸 After fees: ${profit_after_fees:.3f}")
            logger.info(
                "   ⚠️  Note: Gas cost (~$0.50) not included in paper trading simulation"
            )

    except ValueError as e:
        logger.error(f"   ❌ Trade failed: {e}")


if __name__ == "__main__":
    main()
