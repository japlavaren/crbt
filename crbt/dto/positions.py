from decimal import Decimal
from functools import lru_cache
from typing import List, Optional

from crbt.dto.position import Position
from crbt.dto.trade import Trade


class Positions:
    def __init__(self) -> None:
        self._positions: Optional[List[Position]] = None

    def create_positions(self, min_price: Decimal, max_price: Decimal, step_price: Decimal) -> None:
        assert min_price < max_price
        self._positions = []
        price = min_price

        while price < max_price:
            self._positions.append(Position(price))
            price += step_price

        self._positions.append(Position(max_price))

    @property
    def bought_positions(self) -> List[Position]:
        assert self._positions is not None

        return [position for position in self._positions
                if position.trade is not None and position.trade.bought_amount is not None]

    def get_empty_positions_by_prices(self, min_price: Decimal, max_price: Decimal) -> List[Position]:
        assert self._positions is not None

        return [position for position in self._positions
                if position.trade is None and min_price <= position.price <= max_price]

    @lru_cache
    def get_position_by_buy_order_id(self, buy_order_id: int) -> Optional[Position]:
        assert self._positions is not None

        for position in self._positions:
            if position.trade is not None and position.trade.buy_order_id == buy_order_id:
                return position
        else:
            return None

    @lru_cache
    def get_position_by_sell_order_id(self, sell_order_id: int) -> Optional[Position]:
        assert self._positions is not None

        for position in self._positions:
            if position.trade is not None and position.trade.sell_order_id == sell_order_id:
                return position
        else:
            return None

    def remove_position(self, position: Position) -> None:
        assert self._positions is not None
        assert position.sell_only
        self._positions.remove(position)

    def load_trades(self, trades: List[Trade]) -> None:
        assert self._positions is not None
        trades.sort(key=lambda t: t.position_price)
        self._positions.sort(key=lambda p: p.price)

        for trade in trades:
            if not self._load_trade(trade):
                # create sell only position if there is no free position
                self._positions.append(Position(trade.position_price, trade, sell_only=True))

    def _load_trade(self, trade: Trade) -> bool:
        assert self._positions is not None

        for position in self._positions:
            if position.trade is None and position.price >= trade.position_price:
                position.trade = trade
                trade.position_price = position.price

                return True
        else:
            return False

