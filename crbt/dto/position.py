from decimal import Decimal
from typing import Optional

from crbt.dto.trade import Trade


class Position:
    def __init__(self, price: Decimal):
        self.price: Decimal = price
        self.trade: Optional[Trade] = None
