"""Tests for market rebalancing arbitrage strategy."""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from unittest.mock import Mock

import pytest
from hypothesis import given
from hypothesis import strategies as st

from trading.strategies.base import SignalType
from trading.strategies.market_rebalancing import MarketRebalancingStrategy


class TestMarketRebalancingStrategy:
    """Test suite for MarketRebalancingStrategy."""

    @pytest.fixture
    def mock_client(self):
        """Mock Polymarket client."""
        client = Mock()
        client.get_token_price.return_value = 0.5
        return client

    @pytest.fixture
    def strategy(self, mock_client):
        """Create strategy instance."""
        return MarketRebalancingStrategy(
            client=mock_client, min_profit_threshold=0.01, min_confidence=0.8
        )

    def test_strategy_initialization(self, mock_client):
        """Test strategy initializes correctly."""
        strategy = MarketRebalancingStrategy(
            client=mock_client, min_profit_threshold=0.02, min_confidence=0.9
        )

        assert strategy.name == "Market Rebalancing Arbitrage"
        assert strategy.min_profit_threshold == 0.02
        assert strategy.min_confidence == 0.9
        assert strategy.enabled is True
        assert strategy.opportunities_found == 0

    def test_disabled_strategy_returns_empty(self, strategy):
        """Test disabled strategy returns no signals."""
        strategy.disable()

        market_data = {
            "condition_id": "test_market",
            "question": "Test market question",
            "tokens": [
                {"token_id": "yes_token", "outcome": "Yes"},
                {"token_id": "no_token", "outcome": "No"},
            ],
        }

        signals = strategy.analyze(market_data)
        assert signals == []

    def test_missing_market_data_returns_empty(self, strategy):
        """Test strategy handles missing market data gracefully."""
        # Missing condition_id
        market_data = {
            "question": "Test market question",
            "tokens": [
                {"token_id": "yes_token", "outcome": "Yes"},
                {"token_id": "no_token", "outcome": "No"},
            ],
        }

        signals = strategy.analyze(market_data)
        assert signals == []

    def test_missing_tokens_returns_empty(self, strategy):
        """Test strategy handles missing tokens gracefully."""
        market_data = {
            "condition_id": "test_market",
            "question": "Test market question",
            "tokens": [],
        }

        signals = strategy.analyze(market_data)
        assert signals == []

    def test_missing_yes_token_returns_empty(self, strategy):
        """Test strategy handles missing YES token."""
        market_data = {
            "condition_id": "test_market",
            "question": "Test market question",
            "tokens": [{"token_id": "no_token", "outcome": "No"}],
        }

        signals = strategy.analyze(market_data)
        assert signals == []

    def test_missing_no_token_returns_empty(self, strategy):
        """Test strategy handles missing NO token."""
        market_data = {
            "condition_id": "test_market",
            "question": "Test market question",
            "tokens": [{"token_id": "yes_token", "outcome": "Yes"}],
        }

        signals = strategy.analyze(market_data)
        assert signals == []

    def test_price_fetch_failure_returns_empty(self, strategy, mock_client):
        """Test strategy handles price fetch failures."""
        mock_client.get_token_price.return_value = None

        market_data = {
            "condition_id": "test_market",
            "question": "Test market question",
            "tokens": [
                {"token_id": "yes_token", "outcome": "Yes"},
                {"token_id": "no_token", "outcome": "No"},
            ],
        }

        signals = strategy.analyze(market_data)
        assert signals == []

    @pytest.mark.trading
    def test_buy_both_arbitrage_opportunity(self, strategy, mock_client):
        """Test detection of buy-both arbitrage opportunity."""
        # Prices sum to less than $1 (0.4 + 0.5 = 0.9)
        mock_client.get_token_price.side_effect = [0.4, 0.5]

        market_data = {
            "condition_id": "test_market",
            "question": "Test market question",
            "tokens": [
                {"token_id": "yes_token", "outcome": "Yes"},
                {"token_id": "no_token", "outcome": "No"},
            ],
        }

        signals = strategy.analyze(market_data)

        assert len(signals) == 1
        signal = signals[0]
        assert signal.signal_type == SignalType.ARBITRAGE
        assert signal.confidence >= 0.8
        assert signal.metadata is not None

        opportunity = signal.metadata["opportunity"]
        assert opportunity.opportunity_type == "buy_both"
        assert opportunity.price_sum == 0.9
        assert opportunity.profit_potential == pytest.approx(0.1)

    @pytest.mark.trading
    def test_sell_both_arbitrage_opportunity(self, strategy, mock_client):
        """Test detection of sell-both arbitrage opportunity."""
        # Prices sum to more than $1 (0.6 + 0.5 = 1.1)
        mock_client.get_token_price.side_effect = [0.6, 0.5]

        market_data = {
            "condition_id": "test_market",
            "question": "Test market question",
            "tokens": [
                {"token_id": "yes_token", "outcome": "Yes"},
                {"token_id": "no_token", "outcome": "No"},
            ],
        }

        signals = strategy.analyze(market_data)

        assert len(signals) == 1
        signal = signals[0]
        assert signal.signal_type == SignalType.ARBITRAGE
        assert signal.confidence >= 0.8
        assert signal.metadata is not None

        opportunity = signal.metadata["opportunity"]
        assert opportunity.opportunity_type == "sell_both"
        assert opportunity.price_sum == 1.1
        assert opportunity.profit_potential == pytest.approx(0.1)

    def test_no_arbitrage_when_prices_balanced(self, strategy, mock_client):
        """Test no arbitrage detected when prices sum to ~$1."""
        # Prices sum to exactly $1 (0.5 + 0.5 = 1.0)
        mock_client.get_token_price.side_effect = [0.5, 0.5]

        market_data = {
            "condition_id": "test_market",
            "question": "Test market question",
            "tokens": [
                {"token_id": "yes_token", "outcome": "Yes"},
                {"token_id": "no_token", "outcome": "No"},
            ],
        }

        signals = strategy.analyze(market_data)
        assert signals == []

    def test_no_arbitrage_below_profit_threshold(self, strategy, mock_client):
        """Test no arbitrage when profit below threshold."""
        # Prices sum to 0.995 (deviation of 0.005 < 0.01 threshold)
        mock_client.get_token_price.side_effect = [0.495, 0.5]

        market_data = {
            "condition_id": "test_market",
            "question": "Test market question",
            "tokens": [
                {"token_id": "yes_token", "outcome": "Yes"},
                {"token_id": "no_token", "outcome": "No"},
            ],
        }

        signals = strategy.analyze(market_data)
        assert signals == []

    @given(
        yes_price=st.floats(min_value=0.01, max_value=0.99),
        no_price=st.floats(min_value=0.01, max_value=0.99),
    )
    @pytest.mark.trading
    def test_arbitrage_detection_property(self, yes_price, no_price):
        """Property-based test for arbitrage detection logic."""
        # Create mock client for this test
        mock_client = Mock()
        mock_client.get_token_price.side_effect = [yes_price, no_price]

        # Create strategy instance for this test
        strategy = MarketRebalancingStrategy(
            client=mock_client,
            min_profit_threshold=0.01,
            min_confidence=0.1,  # Very low confidence threshold for property test
            max_price_sum_deviation=1.0,  # Allow any deviation
        )

        market_data = {
            "condition_id": "test_market",
            "question": "Test market question",
            "tokens": [
                {"token_id": "yes_token", "outcome": "Yes"},
                {"token_id": "no_token", "outcome": "No"},
            ],
        }

        signals = strategy.analyze(market_data)
        price_sum = yes_price + no_price
        deviation = abs(price_sum - 1.0)

        if deviation >= strategy.min_profit_threshold:
            # Should find arbitrage opportunity if confidence is met
            # Note: confidence calculation: min(1.0, deviation / max_price_sum_deviation)
            confidence = min(1.0, deviation / strategy.max_price_sum_deviation)

            if confidence >= strategy.min_confidence:
                assert len(signals) == 1
                signal = signals[0]
                assert signal.signal_type == SignalType.ARBITRAGE

                opportunity = signal.metadata["opportunity"]
                assert opportunity.price_sum == pytest.approx(price_sum, rel=1e-9)
                assert opportunity.profit_potential == pytest.approx(
                    deviation, rel=1e-9
                )

                if price_sum < 1.0:
                    assert opportunity.opportunity_type == "buy_both"
                else:
                    assert opportunity.opportunity_type == "sell_both"
            else:
                # Confidence too low, should not find opportunity
                assert signals == []
        else:
            # Should not find arbitrage opportunity
            assert signals == []

    def test_opportunities_counter_increments(self, strategy, mock_client):
        """Test that opportunities_found counter increments."""
        mock_client.get_token_price.side_effect = [0.4, 0.5]

        market_data = {
            "condition_id": "test_market",
            "question": "Test market question",
            "tokens": [
                {"token_id": "yes_token", "outcome": "Yes"},
                {"token_id": "no_token", "outcome": "No"},
            ],
        }

        initial_count = strategy.opportunities_found
        strategy.analyze(market_data)
        assert strategy.opportunities_found == initial_count + 1

    def test_get_strategy_description(self, strategy):
        """Test strategy description."""
        description = strategy.get_strategy_description()
        assert "Market Rebalancing Arbitrage" in description
        assert "YES + NO token" in description
        assert "$1.00" in description

    def test_get_stats(self, strategy):
        """Test strategy statistics."""
        stats = strategy.get_stats()

        assert stats["name"] == "Market Rebalancing Arbitrage"
        assert stats["enabled"] is True
        assert "opportunities_found" in stats
        assert isinstance(stats["opportunities_found"], int)
