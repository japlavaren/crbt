from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from crbt.api.api import Api
from crbt.dto.kline import Kline
from crbt.dto.order import Order
from crbt.dto.positions import Positions
from crbt.dto.trade import Trade


class Bot:
    def __init__(self, symbol, api: Api, session: Session) -> None:
        self._symbol: str = symbol
        self._min_buy_price: Optional[Decimal] = None
        self._max_buy_price: Optional[Decimal] = None
        self._step_price: Optional[Decimal] = None
        self._min_profit: Optional[Decimal] = None
        self._kline_margin: Optional[Decimal] = None
        self._trade_amount: Optional[Decimal] = None
        self._api: Api = api
        self._session: Session = session

        self._positions: Positions = Positions()
        self._klines_history: List[Kline] = []
        self._finished_trades: List[Trade] = []
        self._max_investment: Decimal = Decimal(0)

    def load_settings(self, symbol: str, min_buy_price: Decimal, max_buy_price: Decimal, step_price: Decimal,
                      min_profit: Decimal, kline_margin: Decimal, trade_amount: Decimal) -> None:
        if self._symbol is not None:
            assert symbol == self._symbol

        reload_positions = (min_buy_price != self._min_buy_price
                            or max_buy_price != self._max_buy_price
                            or step_price != self._step_price)

        self._symbol = symbol
        self._min_buy_price = min_buy_price
        self._max_buy_price = max_buy_price
        self._step_price = step_price
        self._min_profit = min_profit
        self._kline_margin = kline_margin
        self._trade_amount = trade_amount

        if reload_positions:
            self._load_positions()

    @property
    def statistics(self) -> Dict[str, Any]:
        current_price = self._klines_history[-1].close_price
        bought_positions = self._positions.bought_positions

        # position.trade is defined as optional but in bought_positions is always present
        opened_revenue = sum(position.trade.calculate_revenue(current_price)  # type: ignore
                             for position in bought_positions)

        return dict(
            min_profit=self._min_profit,
            finished_trades=len(self._finished_trades),
            finished_revenue=sum(trade.revenue for trade in self._finished_trades),
            opened_trades=len(bought_positions),
            opened_revenue=opened_revenue,
            max_investment=self._max_investment,
        )

    def process(self, kline: Kline) -> None:
        self._buy_empty_positions(kline)
        self._process_api_orders()
        self._create_sell_orders()
        self._klines_history.append(kline)
        self._max_investment = max(self._investment, self._max_investment)

    @property
    def _investment(self) -> Decimal:
        # position.trade is defined as optional but in bought_positions is always present
        return sum(position.trade.bought_amount for position in self._positions.bought_positions)  # type: ignore

    def _buy_empty_positions(self, kline: Kline) -> None:
        assert self._kline_margin is not None
        assert self._trade_amount is not None
        empty_positions = self._positions.get_empty_positions_by_prices(
            min_price=kline.low_price / (1 + self._kline_margin),
            max_price=kline.high_price * (1 + self._kline_margin),
        )

        for position in empty_positions:
            position.trade = self._api.buy_order(self._symbol, position.price, self._trade_amount)
            self._session.add(position.trade)
            self._session.commit()

    def _process_api_orders(self) -> None:
        for order in self._api.get_orders():
            if order.side == Order.SIDE_BUY:
                self._process_buy_order(order)
            elif order.side == Order.SIDE_SELL:
                self._process_sell_order(order)

    def _process_buy_order(self, order: Order) -> None:
        assert order.side == Order.SIDE_BUY
        position = self._positions.get_position_by_buy_order_id(order.order_id)

        if position is None or position.trade is None:  # position is already sold (result might be cached)
            return
        elif order.status == Order.STATUS_FILLED and position.trade.status == Trade.STATUS_BUY_ORDER:
            position.trade.set_bought(buy_time=order.update_time, buy_price=order.price, buy_message=order.message)
            self._session.commit()

    def _process_sell_order(self, order: Order) -> None:
        assert order.side == Order.SIDE_SELL
        position = self._positions.get_position_by_sell_order_id(order.order_id)

        if position is None or position.trade is None:  # position is already sold (result might be cached)
            return
        elif order.status == Order.STATUS_FILLED and position.trade.status == Trade.STATUS_SELL_ORDER:
            position.trade.set_sold(sell_time=order.update_time, sell_price=order.price, sell_message=order.message)
            self._session.commit()
            self._finished_trades.append(position.trade)
            position.trade = None

            if position.sell_only:
                self._positions.remove_position(position)

    def _create_sell_orders(self) -> None:
        assert self._min_profit is not None

        for position in self._positions.bought_positions:
            assert position.trade is not None

            if position.trade.status == Trade.STATUS_BOUGHT:
                self._api.sell_order(position.trade, sell_price=position.trade.buy_price * (1 + self._min_profit))
                self._session.commit()

    def _load_positions(self) -> None:
        assert self._min_buy_price is not None
        assert self._max_buy_price is not None
        assert self._step_price is not None
        self._positions.create_positions(self._min_buy_price, self._max_buy_price, self._step_price)
        trades = self._session.query(Trade).filter(Trade.symbol == self._symbol,
                                                   Trade.status != Trade.STATUS_SOLD).all()

        if len(trades) != 0:
            self._positions.load_trades(trades)
            self._session.commit()
