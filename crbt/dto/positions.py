from decimal import Decimal
from functools import lru_cache
from typing import List, Optional

from crbt.dto.position import Position


class Positions:
    def __init__(self, min_buy_price: Decimal, max_buy_price: Decimal, step_price: Decimal) -> None:
        assert min_buy_price < max_buy_price
        self._positions: List[Position] = self._create_positions(min_buy_price, max_buy_price, step_price)

    @property
    def bought_positions(self) -> List[Position]:
        return [position for position in self._positions
                if position.trade is not None and position.trade.bought_amount is not None]

    def get_empty_positions_by_prices(self, min_price: Decimal, max_price: Decimal) -> List[Position]:
        return [position for position in self._positions
                if position.trade is None and min_price <= position.price <= max_price]

    @lru_cache
    def get_position_by_buy_order_id(self, buy_order_id: int) -> Optional[Position]:
        for position in self._positions:
            if position.trade is not None and position.trade.buy_order_id == buy_order_id:
                return position
        else:
            return None

    @lru_cache
    def get_position_by_sell_order_id(self, sell_order_id: int) -> Optional[Position]:
        for position in self._positions:
            if position.trade is not None and position.trade.sell_order_id == sell_order_id:
                return position
        else:
            return None

    @staticmethod
    def _create_positions(min_price: Decimal, max_price: Decimal, step_price: Decimal) -> List[Position]:
        positions = []
        price = min_price

        while price < max_price:
            positions.append(Position(price))
            price += step_price

        positions.append(Position(max_price))

        return positions
