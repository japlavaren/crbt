from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional


class Trade:
    STATUS_BUY_ORDER = 'buy-order'
    STATUS_BOUGHT = 'bought'
    STATUS_SELL_ORDER = 'sell-order'
    STATUS_SOLD = 'sold'

    _COMMISSION = Decimal('0.2') / 100

    def __init__(self, symbol: str, position_price: Decimal, quantity: Decimal, buy_order_id: int, buy_price: Decimal,
                 buy_order_time: datetime, message: Dict[str, Any]) -> None:
        self.symbol: str = symbol
        self.position_price: Decimal = position_price
        self.status: str = self.STATUS_BUY_ORDER
        self.quantity: Decimal = quantity
        self.buy_order_id: int = buy_order_id
        self.buy_price: Decimal = buy_price
        self.buy_order_time: datetime = buy_order_time
        self.buy_message: Dict[str, Any] = message
        self.buy_time: Optional[datetime] = None
        self.bought_amount: Optional[Decimal] = None

        self.sell_order_id: Optional[int] = None
        self.sell_price: Optional[Decimal] = None
        self.sell_order_time: Optional[datetime] = None
        self.sell_message: Optional[Dict[str, Any]] = None
        self.sell_time: Optional[datetime] = None

    @property
    def revenue(self) -> Decimal:
        return self.calculate_revenue(self.sell_price)

    def calculate_revenue(self, current_price: Decimal) -> Decimal:
        current_amount = current_price * self.quantity
        commission = self.bought_amount * self._COMMISSION + current_amount * self._COMMISSION

        return current_amount - self.bought_amount - commission

    def set_bought(self, buy_time: datetime, buy_price: Decimal, buy_message: Dict[str, Any]) -> None:
        assert self.status == self.STATUS_BUY_ORDER
        self.status = self.STATUS_BOUGHT
        self.buy_time = buy_time
        self.buy_price = buy_price
        self.buy_message = buy_message
        self.bought_amount = buy_price * self.quantity

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
