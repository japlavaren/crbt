from datetime import datetime
from decimal import Decimal


class Kline:
    def __init__(self, symbol: str, open_time: datetime, close_time: datetime, open_price: Decimal, close_price: Decimal,
                 high_price: Decimal, low_price: Decimal) -> None:
        self.symbol: str = symbol
        self.open_time: datetime = open_time
        self.close_time: datetime = close_time
        self.open_price: Decimal = open_price
        self.close_price: Decimal = close_price
        self.high_price: Decimal = high_price
        self.low_price: Decimal = low_price
