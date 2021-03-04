from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session
from twisted.protocols.amp import Decimal

from crbt.api.api import Api
from crbt.dto.kline import Kline
from crbt.dto.order import Order
from crbt.dto.trade import Trade


class TestingApi(Api):
    PRECISION = 8

    def __init__(self, db_session: Session) -> None:
        self._db_session: Session = db_session
        self._kline: Optional[Kline] = None
        self.__order_id: int = 0

    def set_kline(self, kline: Kline) -> None:
        self._kline = kline

    def limit_buy(self, symbol: str, position: int, price: Decimal, amount: Decimal) -> Trade:
        assert self._kline is not None
        assert self._kline.symbol == symbol
        quantity: Decimal = round(amount / price, self.PRECISION)
        trade = Trade()
        trade.set_buy_order(symbol, position, quantity, self._order_id, price, buy_order_time=self._kline.close_time,
                            buy_message={})

        # trade is immediately bought when price is higher than kline price
        if price >= self._kline.close_price:
            trade.set_bought(buy_time=self._kline.close_time, buy_price=price, buy_message={})

        return trade

    def limit_sell(self, trade: Trade, sell_price: Decimal) -> None:
        assert self._kline is not None
        assert trade.symbol == self._kline.symbol
        trade.set_sell_order(self._order_id, sell_price, sell_order_time=self._kline.close_time, sell_message={})

    def market_sell(self, symbol: str, quantity: Decimal) -> Tuple[datetime, Decimal, Dict[str, Any]]:
        raise NotImplementedError()

    def get_orders(self, symbol: str) -> List[Order]:
        assert self._kline is not None
        assert symbol == self._kline.symbol

        return self._get_bought_orders(symbol) + self._get_sold_orders(symbol)

    def _get_bought_orders(self, symbol: str) -> List[Order]:
        assert self._kline is not None
        trades = self._db_session.query(Trade).filter(
            Trade.symbol == symbol,
            Trade.status == Trade.STATUS_BUY_ORDER,
            Trade.buy_price >= self._kline.low_price,
            Trade.buy_price <= self._kline.high_price,
        ).all()

        return [Order(trade.symbol, Order.SIDE_BUY, Order.STATUS_FILLED, trade.buy_order_id, trade.buy_price,
                      original_qty=trade.quantity, executed_qty=trade.quantity, time=trade.buy_order_time,
                      update_time=self._kline.close_time, message={}) for trade in trades]

    def _get_sold_orders(self, symbol: str) -> List[Order]:
        assert self._kline is not None
        trades = self._db_session.query(Trade).filter(
            Trade.symbol == symbol,
            Trade.status == Trade.STATUS_SELL_ORDER,
            Trade.sell_price >= self._kline.low_price,
            Trade.sell_price <= self._kline.high_price,
        ).all()

        return [Order(trade.symbol, Order.SIDE_SELL, Order.STATUS_FILLED, trade.sell_order_id, trade.sell_price,
                      original_qty=trade.quantity, executed_qty=trade.quantity, time=trade.sell_order_time,
                      update_time=self._kline.close_time, message={}) for trade in trades]

    @property
    def _order_id(self) -> int:
        self.__order_id += 1

        return self.__order_id
