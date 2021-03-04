from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Tuple

from crbt.dto.order import Order
from crbt.dto.trade import Trade


class Api(ABC):
    @abstractmethod
    def limit_buy(self, symbol: str, position: int, price: Decimal, amount: Decimal) -> Trade:
        pass

    @abstractmethod
    def limit_sell(self, trade: Trade, sell_price: Decimal) -> None:
        pass

    @abstractmethod
    def market_sell(self, symbol: str, quantity: Decimal) -> Tuple[datetime, Decimal, Dict[str, Any]]:
        pass

    @abstractmethod
    def get_orders(self, symbol: str) -> List[Order]:
        pass
