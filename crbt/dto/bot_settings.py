from sqlalchemy import Column, Integer, Numeric, String

from crbt.dto.base import Base


class BotSetting(Base):
    __tablename__ = 'bot_settings'
    id = Column(Integer(), primary_key=True, nullable=False)
    symbol = Column(String(10), nullable=False, unique=True)
    min_buy_price = Column(Numeric(14, 8), nullable=False)
    max_buy_price = Column(Numeric(14, 8), nullable=False)
    step_price = Column(Numeric(14, 8), nullable=False)
    min_profit = Column(Numeric(4, 2), nullable=False)
    kline_margin = Column(Numeric(4, 2), nullable=False)
    trade_amount = Column(Numeric(4, 2), nullable=False)
