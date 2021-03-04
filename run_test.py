from datetime import datetime
from decimal import Decimal
from multiprocessing import Pool
from random import choice
from string import ascii_lowercase
from typing import Any, Dict, List, Tuple

from binance.client import Client
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from crbt.api.testing_api import TestingApi
from crbt.bot import Bot
from crbt.dto.base import Base
from crbt.dto.kline import Kline
from crbt.utils import TIME_FORMAT, to_datetime


class TestRunner:
    _UNLIMITED_AMOUNT = Decimal(99_999)

    def __init__(self, test_db_uri: str, client: Client) -> None:
        self._test_db_uri = test_db_uri
        self._client: Client = client

    def run(self, start_time: datetime, end_time: datetime, min_profits: List[Decimal], **settings) -> None:
        klines = self._get_klines(settings['symbol'], start_time, end_time)
        parameters = []

        for min_profit in min_profits:
            bot_settings = settings.copy()
            bot_settings['min_profit'] = min_profit
            parameters.append((bot_settings, klines))

        with Pool(processes=8) as pool:
            statistics = pool.map(self._run_bot, parameters)

        statistics.sort(key=lambda stat: stat['total_revenue'], reverse=True)

        for stat in statistics:
            print(' | '.join([
                f'{stat["symbol"]} {stat["min_profit"]:.1f}%',
                f'revenue: {stat["total_revenue"]:.2f} USDT',
                f'CLOSED revenue: {stat["closed_revenue"]:.2f} USDT, trades: {stat["closed_trades"]}',
                f'OPENED revenue: {stat["opened_revenue"]:.2f} USDT, trades: {stat["opened_trades"]}',
                f'Max investment: {stat["max_investment"]:.2f} USDT',
            ]))

    def _run_bot(self, parameters: Tuple[Dict[str, Any], List[Kline]]) -> Dict[str, Any]:
        settings, klines = parameters
        db_engine, db_name = self._create_test_db()
        db_session = sessionmaker(db_engine)()
        api = TestingApi(db_session)

        try:
            bot = Bot(**settings, active=True, stop_loss=Decimal(0), get_available_amount=self._get_available_amount,
                      db_session=db_session, api=api)

            for kline in klines:
                api.set_kline(kline)
                bot.process(kline)

            statistics = bot.statistics
            statistics['min_profit'] = settings['min_profit']

            return statistics
        finally:
            db_session.close()
            db_engine.execute(f'DROP DATABASE {db_name}')

    @classmethod
    def _get_available_amount(cls) -> Decimal:
        return cls._UNLIMITED_AMOUNT

    def _create_test_db(self) -> Tuple[Engine, str]:
        db_name = 'crbt_test_' + ''.join(choice(ascii_lowercase) for _ in range(6))
        engine = create_engine(self._test_db_uri)
        engine.execute(f'CREATE DATABASE {db_name}')
        engine.execute(f'USE {db_name}')
        Base.metadata.create_all(engine)

        return engine, db_name

    def _get_klines(self, symbol: str, start_time: datetime, end_time: datetime) -> List[Kline]:
        data = self._client.get_historical_klines_generator(symbol, Client.KLINE_INTERVAL_1MINUTE,
                                                            start_str=start_time.strftime(TIME_FORMAT),
                                                            end_str=end_time.strftime(TIME_FORMAT))

        return [Kline(
            symbol,
            open_time=to_datetime(row[0]),
            open_price=Decimal(row[1]),
            high_price=Decimal(row[2]),
            low_price=Decimal(row[3]),
            close_price=Decimal(row[4]),
            close_time=to_datetime(row[6]),
        ) for row in data]


if __name__ == '__main__':
    runner = TestRunner(test_db_uri='mysql://root:root@localhost', client=Client())
    runner.run(
        start_time=datetime(2021, 3, 4, 0, 0),
        end_time=datetime.now(),
        min_profits=[Decimal(3)],
        symbol='ADAUSDT',
        min_buy_price=Decimal(.96),
        max_buy_price=Decimal(1.5),
        step_price=Decimal(0.01),
        kline_margin=Decimal(1),
        trade_amount=Decimal(12),
    )
