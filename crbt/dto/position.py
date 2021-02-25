from decimal import Decimal
from typing import Optional

from crbt.dto.trade import Trade


class Position:
    def __init__(self, price: Decimal, trade: Trade = None, sell_only: bool = False):
        self.price: Decimal = price
        self._trade: Optional[Trade] = trade
        self.sell_only = sell_only

    @property
    def trade(self) -> Optional[Trade]:
        return self._trade

    @trade.setter
    def trade(self, trade: Trade) -> None:
        assert self._trade is None
        assert not self.sell_only
        self._trade = trade
