from datetime import datetime
from decimal import Decimal
from multiprocessing import Pool
from typing import Any, Dict, List, Tuple

from binance.client import Client

from crbt.api.testing_api import TestingApi
from crbt.bot import Bot
from crbt.dto.kline import Kline
from crbt.utils import TIME_FORMAT, to_datetime


class TestRunner:
    def __init__(self) -> None:
        self._client: Client = Client()

    def run(self, start_time: datetime, end_time: datetime, min_profits: List[Decimal], **settings) -> None:
        klines = self._get_klines(settings['symbol'], start_time, end_time)
        parameters = []

        for min_profit in min_profits:
            bot_settings = settings.copy()
            bot_settings['min_profit'] = min_profit
            parameters.append((bot_settings, klines))

        with Pool(processes=8) as pool:
            statistics = pool.map(self._run_bot, parameters)

        statistics.sort(key=lambda stat: stat['finished_revenue'], reverse=True)

        for stat in statistics:
            print(f'{stat["min_profit"] * 100:.1f}% | '
                  f'FINISHED revenue: {stat["finished_revenue"]:.2f} USDT, trades: {stat["finished_trades"]} | '
                  f'OPENED revenue: {stat["opened_revenue"]:.2f} USDT, trades: {stat["opened_trades"]} | '
                  f'Max investment: {stat["max_investment"]:.2f} USDT')

    @staticmethod
    def _run_bot(parameters: Tuple[Dict[str, Any], List[Kline]]) -> Dict[str, Any]:
        settings, klines = parameters
        api = TestingApi()
        bot = Bot(api=api, **settings)

        for kline in klines:
            api.set_kline(kline)
            bot.process(kline)

        return bot.statistics

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
    runner = TestRunner()
    runner.run(
        start_time=datetime(2021, 2, 23, 11, 0),
        end_time=datetime.now(),
        min_profits=[Decimal(p) / 100 for p in [1, 2, 3, 4, 5]],
        symbol='SOLUSDT',
        min_buy_price=Decimal(13.63),
        max_buy_price=Decimal(14.8),
        step_price=Decimal(0.01),
        kline_margin=Decimal(1),
        trade_amount=Decimal(10),
    )
