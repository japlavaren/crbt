from datetime import datetime
from decimal import Decimal
from typing import Any, Dict


class Order:
    SIDE_BUY = 'buy'
    SIDE_SELL = 'sell'

    STATUS_NEW = 'new'
    STATUS_FILLED = 'filled'

    def __init__(self, symbol: str, side: str, status: str, order_id: int, price: Decimal, original_qty: Decimal,
                 executed_qty: Decimal, time: datetime, update_time: datetime, message: Dict[str, Any]) -> None:
        self.symbol: str = symbol
        self.side: str = side
        self.status: str = status
        self.order_id: int = order_id
        self.price: Decimal = price
        self.original_qty: Decimal = original_qty
        self.executed_qty: Decimal = executed_qty
        self.time: datetime = time
        self.update_time: datetime = update_time
        self.message: Dict[str, Any] = message
