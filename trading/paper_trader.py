"""Paper trading implementation."""

import logging
import time
from dataclasses import asdict, dataclass
from enum import Enum

import orjson

logger = logging.getLogger(__name__)


class Side(Enum):
    BUY = "buy"
    SELL = "sell"


class PositionStatus(Enum):
    OPEN = "open"
    CLOSED = "closed"


@dataclass
class PaperOrder:
    """Represents a paper trade order."""

    id: str
    market_id: str
    market_question: str
    side: Side
    size: float
    price: float
    timestamp: float
    crypto_price: float | None = None
    crypto_symbol: str | None = None


@dataclass
class PaperPosition:
    """Represents a paper trading position."""

    id: str
    market_id: str
    market_question: str
    entry_order: PaperOrder
    exit_order: PaperOrder | None = None
    status: PositionStatus = PositionStatus.OPEN

    @property
    def pnl(self) -> float | None:
        """Calculate P&L if position is closed."""
        if self.status != PositionStatus.CLOSED or not self.exit_order:
            return None

        if self.entry_order.side == Side.BUY:
            # Bought YES tokens, sold them
            return (
                self.exit_order.price - self.entry_order.price
            ) * self.entry_order.size
        else:
            # Sold YES tokens (short), bought them back
            return (
                self.entry_order.price - self.exit_order.price
            ) * self.entry_order.size


class PaperTrader:
    """Paper trading system for tracking virtual trades."""

    def __init__(self, initial_balance: float = 10000.0):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.positions: list[PaperPosition] = []
        self.orders: list[PaperOrder] = []
        self.token_inventory: dict[str, float] = {}  # token_id -> quantity
        self._next_order_id = 1
        self._next_position_id = 1

    def place_order(
        self,
        market_id: str,
        market_question: str,
        side: Side,
        size: float,
        price: float,
        token_id: str | None = None,
        crypto_price: float | None = None,
        crypto_symbol: str | None = None,
    ) -> PaperOrder:
        """Place a paper trade order.

        Args:
            market_id: Market identifier
            market_question: Question text
            side: BUY or SELL
            size: Order size (number of tokens)
            price: Price per token
            token_id: Token ID (required for SELL orders to check inventory)
            crypto_price: Optional crypto price at time of order
            crypto_symbol: Optional crypto symbol

        Returns:
            PaperOrder object

        Raises:
            ValueError: If SELL order without sufficient tokens
        """
        # For SELL orders, verify token inventory
        if side == Side.SELL and token_id:
            token_balance = self.token_inventory.get(token_id, 0)
            if token_balance < size:
                raise ValueError(
                    f"Insufficient tokens: need {size:.2f}, have {token_balance:.2f}"
                )
            # Deduct tokens from inventory
            self.token_inventory[token_id] -= size

        order = PaperOrder(
            id=str(self._next_order_id),
            market_id=market_id,
            market_question=market_question,
            side=side,
            size=size,
            price=price,
            timestamp=time.time(),
            crypto_price=crypto_price,
            crypto_symbol=crypto_symbol,
        )
        self._next_order_id += 1

        # Create position
        position = PaperPosition(
            id=str(self._next_position_id),
            market_id=market_id,
            market_question=market_question,
            entry_order=order,
        )
        self._next_position_id += 1

        # Update balance
        if side == Side.BUY:
            # BUY: Pay USDC, receive tokens (CLOB mints automatically)
            cost = size * price
            self.balance -= cost
            # Add tokens to inventory (simulating CLOB mint)
            if token_id:
                self.token_inventory[token_id] = (
                    self.token_inventory.get(token_id, 0) + size
                )
        else:
            # SELL: Deliver tokens, receive USDC (CLOB burns)
            proceeds = size * price
            self.balance += proceeds
            # Tokens already deducted above

        self.orders.append(order)
        self.positions.append(position)

        action_amount = size * price
        logger.info(
            "Paper trade placed: %s %.2f @ $%.3f ($%.2f)",
            side.value.upper(),
            size,
            price,
            action_amount,
        )
        logger.info("Balance: $%.2f", self.balance)
        if token_id:
            logger.info(
                "Token %s... balance: %.2f",
                token_id[:8],
                self.token_inventory.get(token_id, 0),
            )

        return order

    def close_position(
        self, position_id: str, exit_price: float
    ) -> PaperPosition | None:
        """Close an open position."""
        position = next((p for p in self.positions if p.id == position_id), None)
        if not position or position.status != PositionStatus.OPEN:
            return None

        # Create exit order (opposite side)
        exit_side = Side.SELL if position.entry_order.side == Side.BUY else Side.BUY
        exit_order = PaperOrder(
            id=str(self._next_order_id),
            market_id=position.market_id,
            market_question=position.market_question,
            side=exit_side,
            size=position.entry_order.size,
            price=exit_price,
            timestamp=time.time(),
        )
        self._next_order_id += 1

        position.exit_order = exit_order
        position.status = PositionStatus.CLOSED

        # Update balance with proceeds
        proceeds = (
            position.entry_order.size * exit_price
            if exit_side == Side.SELL
            else position.entry_order.size * (1 - exit_price)
        )
        self.balance += proceeds

        pnl = position.pnl or 0
        logger.info("Position closed: P&L $%.2f, Balance: $%.2f", pnl, self.balance)

        self.orders.append(exit_order)
        return position

    def split_usdc(self, amount: float, yes_token_id: str, no_token_id: str) -> bool:
        """Simulate splitting USDC into YES + NO tokens.

        This simulates the CTF splitPosition() operation where USDC is converted
        into a complete set of conditional tokens (YES + NO).

        Args:
            amount: USDC amount to split (will create amount of each token)
            yes_token_id: Token ID for YES token
            no_token_id: Token ID for NO token

        Returns:
            True if split was successful, False if insufficient balance
        """
        if self.balance < amount:
            logger.warning(
                "Insufficient balance: need $%.2f, have $%.2f", amount, self.balance
            )
            return False

        # Deduct USDC from balance
        self.balance -= amount

        # Add tokens to inventory
        self.token_inventory[yes_token_id] = (
            self.token_inventory.get(yes_token_id, 0) + amount
        )
        self.token_inventory[no_token_id] = (
            self.token_inventory.get(no_token_id, 0) + amount
        )

        logger.info(
            "Split $%.2f USDC → %.2f YES + %.2f NO tokens", amount, amount, amount
        )
        logger.info("Balance: $%.2f", self.balance)
        logger.info(
            "Token inventory: YES=%.2f, NO=%.2f",
            self.token_inventory.get(yes_token_id, 0),
            self.token_inventory.get(no_token_id, 0),
        )

        return True

    def merge_tokens(self, amount: float, yes_token_id: str, no_token_id: str) -> bool:
        """Simulate merging YES + NO tokens back into USDC.

        This simulates the CTF mergePositions() operation where a complete set
        of conditional tokens is burned to reclaim USDC.

        Args:
            amount: Number of complete sets to merge (needs amount of each token)
            yes_token_id: Token ID for YES token
            no_token_id: Token ID for NO token

        Returns:
            True if merge was successful, False if insufficient tokens
        """
        yes_balance = self.token_inventory.get(yes_token_id, 0)
        no_balance = self.token_inventory.get(no_token_id, 0)

        if yes_balance < amount or no_balance < amount:
            logger.warning(
                "Insufficient tokens: need %.2f of each, have YES=%.2f, NO=%.2f",
                amount,
                yes_balance,
                no_balance,
            )
            return False

        # Burn tokens from inventory
        self.token_inventory[yes_token_id] -= amount
        self.token_inventory[no_token_id] -= amount

        # Add USDC to balance
        self.balance += amount

        logger.info("Merged %.2f YES + %.2f NO → $%.2f USDC", amount, amount, amount)
        logger.info("Balance: $%.2f", self.balance)

        return True

    def apply_fee(self, profit: float, fee_rate: float = 0.0) -> float:
        """Apply Polymarket fee on profits only.

        As of 2025, Polymarket has 0% fees across all volume levels.
        This method is kept for future flexibility if fees are reintroduced.

        Args:
            profit: The profit amount (can be negative)
            fee_rate: The fee rate (default 0.0 = 0%)

        Returns:
            Profit after fees
        """
        if profit <= 0:
            return profit  # No fees on losses
        return profit * (1 - fee_rate)

    def get_open_positions(self) -> list[PaperPosition]:
        """Get all open positions."""
        return [p for p in self.positions if p.status == PositionStatus.OPEN]

    def get_closed_positions(self) -> list[PaperPosition]:
        """Get all closed positions."""
        return [p for p in self.positions if p.status == PositionStatus.CLOSED]

    def get_total_pnl(self) -> float:
        """Get total realized P&L."""
        return sum(p.pnl or 0 for p in self.get_closed_positions())

    def get_stats(self) -> dict:
        """Get trading statistics."""
        closed_positions = self.get_closed_positions()
        total_trades = len(closed_positions)

        if total_trades == 0:
            return {
                "total_trades": 0,
                "total_pnl": 0,
                "win_rate": 0,
                "avg_win": 0,
                "avg_loss": 0,
                "current_balance": self.balance,
                "total_return": 0,
            }

        pnls = [p.pnl or 0 for p in closed_positions]
        wins = [pnl for pnl in pnls if pnl > 0]
        losses = [pnl for pnl in pnls if pnl < 0]

        return {
            "total_trades": total_trades,
            "total_pnl": sum(pnls),
            "win_rate": len(wins) / total_trades * 100,
            "avg_win": sum(wins) / len(wins) if wins else 0,
            "avg_loss": sum(losses) / len(losses) if losses else 0,
            "current_balance": self.balance,
            "total_return": (self.balance - self.initial_balance)
            / self.initial_balance
            * 100,
        }

    def save_to_file(self, filename: str) -> None:
        """Save trading data to JSON file."""
        data = {
            "initial_balance": self.initial_balance,
            "current_balance": self.balance,
            "orders": [asdict(order) for order in self.orders],
            "positions": [asdict(position) for position in self.positions],
            "stats": self.get_stats(),
        }

        # Convert enums to strings for JSON serialization
        for order_dict in data["orders"]:  # type: ignore[attr-defined]
            order_dict["side"] = (
                order_dict["side"].value
                if hasattr(order_dict["side"], "value")
                else order_dict["side"]
            )

        for position_dict in data["positions"]:  # type: ignore[attr-defined]
            position_dict["status"] = (
                position_dict["status"].value
                if hasattr(position_dict["status"], "value")
                else position_dict["status"]
            )
            if position_dict["entry_order"]["side"]:
                position_dict["entry_order"]["side"] = (
                    position_dict["entry_order"]["side"].value
                    if hasattr(position_dict["entry_order"]["side"], "value")
                    else position_dict["entry_order"]["side"]
                )
            if position_dict["exit_order"] and position_dict["exit_order"]["side"]:
                position_dict["exit_order"]["side"] = (
                    position_dict["exit_order"]["side"].value
                    if hasattr(position_dict["exit_order"]["side"], "value")
                    else position_dict["exit_order"]["side"]
                )

        with open(filename, "wb") as f:
            f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))

        logger.info("Trading data saved to %s", filename)
