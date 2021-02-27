from typing import List, Optional

from twisted.protocols.amp import Decimal

from crbt.api.api import Api
from crbt.dto.kline import Kline
from crbt.dto.order import Order
from crbt.dto.trade import Trade


class TestingApi(Api):
    PRECISION = 8

    def __init__(self) -> None:
        self._kline: Optional[Kline] = None
        self._trades: List[Trade] = []
        self.__order_id: int = 0

    def set_kline(self, kline: Kline) -> None:
        self._kline = kline

    def buy_order(self, symbol: str, price: Decimal, amount: Decimal) -> Trade:
        assert self._kline is not None
        assert self._kline.symbol == symbol
        quantity: Decimal = round(amount / price, self.PRECISION)
        trade = Trade()
        trade.set_buy_order(symbol, price, quantity, self._order_id, price, buy_order_time=self._kline.close_time,
                            buy_message={})
        self._trades.append(trade)

        # trade is immediately bought when price is higher than kline price
        if price >= self._kline.close_price:
            trade.set_bought(buy_time=self._kline.close_time, buy_price=price, buy_message={})

        return trade

    def sell_order(self, trade: Trade, sell_price: Decimal) -> None:
        assert trade in self._trades
        assert self._kline is not None
        assert trade.symbol == self._kline.symbol
        trade.set_sell_order(self._order_id, sell_price, sell_order_time=self._kline.close_time, sell_message={})

    def get_orders(self, symbol: str) -> List[Order]:
        assert self._kline is not None
        assert symbol == self._kline.symbol
        orders = []

        for trade in self._trades:
            if trade.status == Trade.STATUS_BUY_ORDER:
                if self._kline.low_price <= trade.buy_price <= self._kline.high_price:  # buy filled
                    orders.append(Order(trade.symbol, Order.SIDE_BUY, Order.STATUS_FILLED, trade.buy_order_id,
                                        trade.buy_price, original_qty=trade.quantity, executed_qty=trade.quantity,
                                        time=trade.buy_order_time, update_time=self._kline.close_time, message={}))

            if trade.status == Trade.STATUS_SELL_ORDER:
                assert trade.sell_price is not None

                if self._kline.low_price <= trade.sell_price <= self._kline.high_price:  # sell filled
                    assert trade.sell_order_id is not None
                    assert trade.sell_order_time is not None
                    orders.append(Order(trade.symbol, Order.SIDE_SELL, Order.STATUS_FILLED, trade.sell_order_id,
                                        trade.sell_price, original_qty=trade.quantity, executed_qty=trade.quantity,
                                        time=trade.sell_order_time, update_time=self._kline.close_time, message={}))

        return orders

    @property
    def _order_id(self) -> int:
        self.__order_id += 1

        return self.__order_id
