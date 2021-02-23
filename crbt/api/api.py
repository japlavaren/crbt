from abc import ABC, abstractmethod
from decimal import Decimal
from typing import List

from crbt.dto.order import Order
from crbt.dto.trade import Trade


class Api(ABC):
    @abstractmethod
    def buy_order(self, symbol: str, price: Decimal, amount: Decimal) -> Trade:
        pass

    @abstractmethod
    def sell_order(self, trade: Trade, sell_price: Decimal) -> None:
        pass

    @abstractmethod
    def get_orders(self) -> List[Order]:
        pass
