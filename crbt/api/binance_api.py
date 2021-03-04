import math
from datetime import datetime
from decimal import Decimal
from functools import lru_cache
from typing import Any, Dict, List, Tuple

from binance.client import Client

from crbt.api.api import Api
from crbt.dto.order import Order
from crbt.dto.trade import Trade
from crbt.utils import to_datetime


class BinanceApi(Api):
    _ORDER_SIDES = {
        'BUY': Order.SIDE_BUY,
        'SELL': Order.SIDE_SELL,
    }
    _ORDER_STATUSES = {
        'NEW': Order.STATUS_NEW,
        'FILLED': Order.STATUS_FILLED,
        'CANCELED': Order.STATUS_CANCELED,
    }

    def __init__(self, binance_client: Client) -> None:
        self._client: Client = binance_client

    def limit_buy(self, symbol: str, position: int, price: Decimal, amount: Decimal) -> Trade:
        quantity: Decimal = round(amount / price, self._get_quantity_precision(symbol))  # type: ignore
        info = self._client.order_limit_buy(symbol=symbol, price=price, quantity=quantity)
        trade = Trade()
        trade.set_buy_order(symbol=info['symbol'], position=position, quantity=Decimal(info['origQty']),
                            buy_order_id=info['orderId'], buy_price=Decimal(info['price']),
                            buy_order_time=to_datetime(info['transactTime']), buy_message=info)

        if Decimal(info['executedQty']) != 0:
            trade.set_bought(buy_time=to_datetime(info['transactTime']), buy_price=Decimal(info['price']),
                             buy_message=info)

        return trade

    def limit_sell(self, trade: Trade, sell_price: Decimal) -> None:
        price: Decimal = round(sell_price, self._get_price_precision(trade.symbol))  # type: ignore
        info = self._client.order_limit_sell(symbol=trade.symbol, price=price, quantity=trade.quantity)
        trade.set_sell_order(sell_order_id=info['orderId'], sell_price=Decimal(info['price']),
                             sell_order_time=to_datetime(info['transactTime']), sell_message=info)

    def market_sell(self, symbol: str, quantity: Decimal) -> Tuple[datetime, Decimal, Dict[str, Any]]:
        quantity = round(quantity, self._get_quantity_precision(symbol))  # type: ignore
        info = self._client.order_market_sell(symbol=symbol, quantity=quantity)
        sell_time = to_datetime(info['transactTime'])
        sell_price = Decimal(info['cummulativeQuoteQty']) / Decimal(info['executedQty'])

        return sell_time, sell_price, info

    def get_orders(self, symbol: str) -> List[Order]:
        return [Order(
            symbol=info['symbol'],
            side=self._ORDER_SIDES[info['side']],
            status=self._ORDER_STATUSES[info['status']],
            order_id=info['orderId'],
            price=Decimal(info['price']),
            original_qty=Decimal(info['origQty']),
            executed_qty=Decimal(info['executedQty']),
            time=to_datetime(info['time']),
            update_time=to_datetime(info['updateTime']),
            message=info,
        ) for info in self._client.get_all_orders(symbol=symbol)]

    def _get_quantity_precision(self, symbol: str) -> int:
        return self._get_precision(symbol, filter_type='LOT_SIZE', step_key='stepSize')

    def _get_price_precision(self, symbol: str) -> int:
        return self._get_precision(symbol, filter_type='PRICE_FILTER', step_key='tickSize')

    @lru_cache
    def _get_precision(self, symbol: str, filter_type: str, step_key: str) -> int:
        info = self._client.get_symbol_info(symbol)

        for f in info['filters']:
            if f['filterType'] == filter_type:
                return int(round(-math.log(Decimal(f[step_key]), 10), 0))
        else:
            raise Exception(f'Unknown precision for {symbol}')
