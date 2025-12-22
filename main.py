"""Main entry point for the polyarb trading bot."""

from typing import Any

from dotenv import load_dotenv

from client import PolymarketClient
from trading import MarketRebalancingStrategy, PaperTrader
from utils import Config, setup_logging

# Load environment variables
load_dotenv()


def main() -> None:
    """Main application entry point."""
    # Setup configuration and logging
    config = Config.from_env()
    logger = setup_logging(level="INFO")

    if not config.validate():
        logger.error("Configuration validation failed")
        return

    logger.info("Starting polyarb trading bot...")

    # Initialize components
    client = PolymarketClient(config.polymarket_host, config.polymarket_chain_id)
    paper_trader = PaperTrader(config.initial_balance)

    # Initialize market rebalancing strategy
    rebalancing_strategy = MarketRebalancingStrategy(
        client=client, min_profit_threshold=0.01, min_confidence=0.8
    )

    logger.info("Scanning markets for arbitrage opportunities...")

    # Get all markets
    response = client.get_markets()
    markets = response.get("data", [])
    logger.info(f"Analyzing {len(markets)} markets...")

    opportunities_found = 0

    # Analyze each market for arbitrage
    for i, market in enumerate(markets[:50]):  # Limit to first 50 for testing
        market_question = market.get("question", "Unknown")
        logger.info(f"[{i + 1}/50] Analyzing: {market_question[:80]}...")

        try:
            # Analyze market with rebalancing strategy
            signals = rebalancing_strategy.analyze(market)

            if signals:
                opportunities_found += 1
                signal = signals[0]  # Take first signal
                if signal.metadata is None:
                    continue
                opportunity = signal.metadata["opportunity"]

                logger.info("🚨 ARBITRAGE OPPORTUNITY FOUND!")
                logger.info(f"   Market: {opportunity.market_question}")
                logger.info(f"   YES Price: ${opportunity.yes_price:.3f}")
                logger.info(f"   NO Price: ${opportunity.no_price:.3f}")
                logger.info(f"   Price Sum: ${opportunity.price_sum:.3f}")
                logger.info(f"   Profit Potential: ${opportunity.profit_potential:.3f}")
                logger.info(f"   Confidence: {opportunity.confidence:.2%}")
                logger.info(f"   Strategy: {opportunity.opportunity_type}")
                print()

                # In paper trading mode, simulate the trade
                if config.paper_trading:
                    simulate_arbitrage_trade(paper_trader, opportunity, logger)

        except Exception as e:
            logger.warning(f"Error analyzing market: {e}")
            continue

    logger.info(f"Scan complete. Found {opportunities_found} arbitrage opportunities.")

    if opportunities_found > 0:
        stats = paper_trader.get_stats()
        logger.info(f"Paper trading results: {stats}")
        paper_trader.save_to_file("arbitrage_trades.json")


def simulate_arbitrage_trade(paper_trader: Any, opportunity: Any, logger: Any) -> None:
    """Simulate placing an arbitrage trade."""
    from trading.paper_trader import Side

    # For simplicity, simulate buying $10 worth of tokens
    trade_amount = 10.0

    if opportunity.opportunity_type == "buy_both":
        # Buy both YES and NO tokens
        yes_order = paper_trader.place_order(
            market_id=opportunity.market_id,
            market_question=opportunity.market_question,
            side=Side.BUY,
            size=trade_amount / opportunity.yes_price,
            price=opportunity.yes_price,
        )

        no_order = paper_trader.place_order(
            market_id=opportunity.market_id,
            market_question=opportunity.market_question + " (NO)",
            side=Side.BUY,
            size=trade_amount / opportunity.no_price,
            price=opportunity.no_price,
        )

        logger.info(
            f"   📈 Simulated buying both tokens (Orders: {yes_order.id}, {no_order.id})"
        )

    elif opportunity.opportunity_type == "sell_both":
        # Sell both YES and NO tokens (short)
        yes_order = paper_trader.place_order(
            market_id=opportunity.market_id,
            market_question=opportunity.market_question,
            side=Side.SELL,
            size=trade_amount / opportunity.yes_price,
            price=opportunity.yes_price,
        )

        no_order = paper_trader.place_order(
            market_id=opportunity.market_id,
            market_question=opportunity.market_question + " (NO)",
            side=Side.SELL,
            size=trade_amount / opportunity.no_price,
            price=opportunity.no_price,
        )

        logger.info(
            f"   📉 Simulated shorting both tokens (Orders: {yes_order.id}, {no_order.id})"
        )


if __name__ == "__main__":
    main()
