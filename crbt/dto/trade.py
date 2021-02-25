from datetime import datetime
from decimal import Decimal
from functools import cached_property
from typing import Dict, Any

from sqlalchemy import Column, DateTime, Integer, JSON, Numeric, String

from crbt.dto.base import Base


class Trade(Base):
    STATUS_BUY_ORDER = 'buy-order'
    STATUS_BOUGHT = 'bought'
    STATUS_SELL_ORDER = 'sell-order'
    STATUS_SOLD = 'sold'

    _COMMISSION = Decimal('0.2') / 100

    __tablename__ = 'trades'
    id = Column(Integer(), primary_key=True, nullable=False)
    symbol = Column(String(10), nullable=False)
    position_price = Column(Numeric(14, 8), nullable=False)
    status = Column(String(10), nullable=False)
    quantity = Column(Numeric(14, 8), nullable=False)
    buy_order_id = Column(Integer(), nullable=False)
    buy_price = Column(Numeric(14, 8), nullable=False)
    buy_order_time = Column(DateTime(), nullable=False)
    buy_message = Column(JSON(), nullable=False)
    buy_time = Column(DateTime())
    sell_order_id = Column(Integer())
    sell_price = Column(Numeric(14, 8))
    sell_order_time = Column(DateTime())
    sell_message = Column(JSON())
    sell_time = Column(DateTime())

    @property
    def revenue(self) -> Decimal:
        return self.calculate_revenue(self.sell_price)

    @cached_property
    def bought_amount(self) -> Decimal:
        assert self.buy_price is not None

        return self.buy_price * self.quantity

    def calculate_revenue(self, current_price: Decimal) -> Decimal:
        current_amount = current_price * self.quantity
        commission = self.bought_amount * self._COMMISSION + current_amount * self._COMMISSION

        return current_amount - self.bought_amount - commission

    def set_buy_order(self, symbol: str, position_price: Decimal, quantity: Decimal, buy_order_id: int,
                      buy_price: Decimal, buy_order_time: datetime, buy_message: Dict[str, Any]) -> None:
        assert self.status is None
        self.status = self.STATUS_BUY_ORDER
        self.symbol = symbol
        self.position_price = position_price
        self.quantity = quantity
        self.buy_order_id = buy_order_id
        self.buy_price = buy_price
        self.buy_order_time = buy_order_time
        self.buy_message = buy_message

    def set_bought(self, buy_time: datetime, buy_price: Decimal, buy_message: Dict[str, Any]) -> None:
        assert self.status == self.STATUS_BUY_ORDER
        self.status = self.STATUS_BOUGHT
        self.buy_time = buy_time
        self.buy_price = buy_price
        self.buy_message = buy_message

    def set_sell_order(self, sell_order_id: int, sell_price: Decimal, sell_order_time: datetime,
                       sell_message: Dict[str, Any]) -> None:
        assert self.status == self.STATUS_BOUGHT
        self.status = self.STATUS_SELL_ORDER
        self.sell_order_id = sell_order_id
        self.sell_price = sell_price
        self.sell_order_time = sell_order_time
        self.sell_message = sell_message

    def set_sold(self, sell_time: datetime, sell_price: Decimal, sell_message: Dict[str, Any]) -> None:
        assert self.status == self.STATUS_SELL_ORDER
        self.status = self.STATUS_SOLD
        self.sell_time = sell_time
        self.sell_price = sell_price
        self.sell_message = sell_message
