from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from crbt.api.api import Api
from crbt.dto.bot_settings import BotSetting
from crbt.dto.kline import Kline
from crbt.dto.order import Order
from crbt.dto.trade import Trade


class Bot:
    POSITION_MULTIPLIER = 10_000

    def __init__(self, symbol: str, active: bool, min_buy_price: Decimal, max_buy_price: Decimal, step_price: Decimal,
                 kline_margin: Decimal, min_profit: Decimal, stop_loss: Decimal, trade_amount: Decimal,
                 get_available_amount: Callable[[], Decimal], db_session: Session, api: Api) -> None:
        self._symbol: str = symbol
        self._active: bool = active
        self._min_buy_price: Decimal = min_buy_price
        self._max_buy_price: Decimal = max_buy_price
        self._step_price: Decimal = step_price
        self._kline_margin: Decimal = 1 + (kline_margin / 100)
        self._min_profit: Decimal = 1 + (min_profit / 100)
        self._stop_loss: Decimal = stop_loss
        self._trade_amount: Decimal = trade_amount
        self._get_available_amount: Callable[[], Decimal] = get_available_amount
        self._db_session: Session = db_session
        self._api: Api = api
        self._last_kline: Optional[Kline] = None

    def load_settings(self, symbol: str, active: bool, min_buy_price: Decimal, max_buy_price: Decimal,
                      step_price: Decimal, kline_margin: Decimal, min_profit: Decimal, stop_loss: Decimal,
                      trade_amount: Decimal) -> None:
        assert self._symbol == symbol
        assert self._step_price == step_price
        self._symbol = symbol
        self._active = active
        self._min_buy_price = min_buy_price
        self._max_buy_price = max_buy_price
        self._step_price = step_price
        self._kline_margin = 1 + (kline_margin / 100)
        self._min_profit = 1 + (min_profit / 100)
        self._stop_loss = stop_loss
        self._trade_amount = trade_amount

    @property
    def statistics(self) -> Dict[str, Any]:
        assert self._last_kline is not None

        closed = self._db_session.execute(
            '''
            SELECT COUNT(*) AS trades, SUM((sell_price - buy_price) * quantity) AS revenue
            FROM trades WHERE symbol = :symbol AND status = :sold
            ''',
            dict(symbol=self._symbol, sold=Trade.STATUS_SOLD)
        ).first()

        last_price = self._last_kline.close_price
        opened = self._db_session.execute(
            '''
            SELECT COUNT(*) AS trades, SUM((:current_price - buy_price) * quantity) AS revenue
            FROM trades WHERE symbol = :symbol AND status IN (:bought, :sell_order)
            ''',
            dict(symbol=self._symbol, current_price=last_price, bought=Trade.STATUS_BOUGHT,
                 sell_order=Trade.STATUS_SELL_ORDER)
        ).first()

        invested = self._db_session.execute(
            '''
            SELECT MAX(amount) AS max_investment FROM (
                SELECT SUM(v.buy_price * v.quantity) AS amount
                FROM trades AS t
                JOIN trades AS v ON v.symbol = t.symbol AND v.buy_time IS NOT NULL AND v.buy_time <= t.buy_time
                    AND (v.sell_time IS NULL OR v.sell_time >= t.buy_time)
                WHERE t.symbol = :symbol
                GROUP BY t.buy_time
                ORDER BY t.buy_time
            ) AS s
            ''',
            dict(symbol=self._symbol)
        ).first()

        return dict(
            symbol=self._symbol,
            total_revenue=closed.revenue + opened.revenue,
            closed_trades=closed.trades, closed_revenue=closed.revenue,
            opened_trades=opened.trades, opened_revenue=opened.revenue,
            max_investment=invested.max_investment,
            out_of_range=not self._min_buy_price <= last_price <= self._max_buy_price,
            no_funds=self._get_available_amount() < self._trade_amount,
        )

    def process(self, kline: Kline) -> None:
        self._check_stop_loss(kline)
        self._buy_empty_positions(kline)
        self._process_api_orders()
        self._create_sell_orders()
        self._last_kline = kline

    def _check_stop_loss(self, kline: Kline) -> None:
        if not self._active or kline.close_price >= self._stop_loss:
            return

        trades = self._db_session.query(Trade).filter(
            Trade.symbol == self._symbol,
            Trade.status.in_([Trade.STATUS_BOUGHT, Trade.STATUS_SELL_ORDER])
        ).all()

        quantity: Decimal = sum(trade.quantity for trade in trades)  # type: ignore
        sell_time, sell_price, sell_message = self._api.market_sell(self._symbol, quantity)

        for trade in trades:
            trade.set_sold(sell_time, sell_price, sell_message, force=True)

        settings: BotSetting = self._db_session.query(BotSetting).filter(
            BotSetting.symbol == self._symbol,
        ).first()
        self._active = settings.active = False
        self._db_session.commit()

    def _buy_empty_positions(self, kline: Kline) -> None:
        if not self._active:
            return

        kline_positions = self._get_positions(kline)
        trades_positions = [trade.position for trade in self._get_trades_by_positions(kline_positions)]
        empty_positions = [position for position in kline_positions if position not in trades_positions]

        if len(empty_positions) != 0:
            available_amount = self._get_available_amount()

            try:
                for position in empty_positions:
                    if available_amount < self._trade_amount:
                        break

                    price = self._get_price_by_position(position)
                    trade = self._api.limit_buy(self._symbol, position, price, self._trade_amount)
                    self._db_session.add(trade)
                    available_amount -= self._trade_amount

                    if trade.status == Trade.STATUS_BOUGHT:
                        self._create_sell_order(trade)
            finally:
                self._db_session.commit()

    def _get_trades_by_positions(self, positions: List[int]) -> List[Trade]:
        assert len(positions) != 0
        return self._db_session.query(Trade).filter(
            Trade.symbol == self._symbol,
            Trade.position.in_(positions),
            Trade.status.in_([Trade.STATUS_BUY_ORDER, Trade.STATUS_BOUGHT, Trade.STATUS_SELL_ORDER])
        ).all()

    def _get_positions(self, kline: Kline) -> List[int]:
        high_price = min(kline.high_price * self._kline_margin, self._max_buy_price)
        low_price = max(kline.low_price / self._kline_margin, self._min_buy_price)
        high_value = self._get_position_by_price(high_price)
        low_value = self._get_position_by_price(low_price)

        if low_value >= high_value:
            return []

        step_value = int(self._step_price * self.POSITION_MULTIPLIER)

        return list(range(low_value, high_value + step_value, step_value))

    def _get_position_by_price(self, price: Decimal) -> int:
        return int(round(price / self._step_price) * self._step_price * self.POSITION_MULTIPLIER)

    def _get_price_by_position(self, position: int) -> Decimal:
        return Decimal(position) / self.POSITION_MULTIPLIER

    def _create_sell_order(self, trade: Trade) -> None:
        assert trade.status == Trade.STATUS_BOUGHT

        sell_price = trade.buy_price * self._min_profit
        self._api.limit_sell(trade, sell_price)

    def _process_api_orders(self) -> None:
        orders = self._api.get_orders(self._symbol)

        if len(orders) != 0:
            try:
                for order in orders:
                    if order.side == Order.SIDE_BUY:
                        self._process_buy_order(order)
                    elif order.side == Order.SIDE_SELL:
                        self._process_sell_order(order)
            finally:
                self._db_session.commit()

    def _process_buy_order(self, order: Order) -> None:
        assert order.side == Order.SIDE_BUY

        if order.status == Order.STATUS_FILLED:
            trade = self._db_session.query(Trade).filter(
                Trade.symbol == self._symbol,
                Trade.buy_order_id == order.order_id,
                Trade.status == Trade.STATUS_BUY_ORDER
            ).first()

            if trade is not None:
                trade.set_bought(buy_time=order.update_time, buy_price=order.price, buy_message=order.message)

    def _process_sell_order(self, order: Order) -> None:
        assert order.side == Order.SIDE_SELL

        if order.status == Order.STATUS_FILLED:
            trade = self._db_session.query(Trade).filter(
                Trade.symbol == self._symbol,
                Trade.sell_order_id == order.order_id,
                Trade.status == Trade.STATUS_SELL_ORDER,
            ).first()

            if trade is not None:
                trade.set_sold(sell_time=order.update_time, sell_price=order.price, sell_message=order.message)

    def _create_sell_orders(self) -> None:
        trades = self._db_session.query(Trade).filter(
            Trade.symbol == self._symbol,
            Trade.status == Trade.STATUS_BOUGHT,
        ).all()

        if len(trades) != 0:
            try:
                for trade in trades:
                    self._create_sell_order(trade)
            finally:
                self._db_session.commit()
