from argparse import ArgumentParser
from decimal import Decimal
from queue import Empty, Queue
from time import time
from typing import Dict, List

from binance.client import Client
from binance.websockets import BinanceSocketManager
from sqlalchemy.orm import Session, sessionmaker

from crbt.api.api import Api
from crbt.bot import Bot
from crbt.di import Di
from crbt.dto.bot_settings import BotSetting
from crbt.dto.kline import Kline
from crbt.utils import to_datetime


class BotRunner:
    _RELOAD_SETTINGS_INTERVAL = 60
    _REPORT_INTERVAL = 5 * 60

    def __init__(self, binance_client: Client, api: Api, db_session: Session) -> None:
        self._socket_manager: BinanceSocketManager = BinanceSocketManager(binance_client)
        self._api: Api = api
        self._db_session: Session = db_session
        self._bots: Dict[str, Bot] = {}
        self._klines_queue: Queue = Queue()
        self._total_amount: Decimal = Decimal(0)
        self._reload_settings_time: float = 0
        self._report_time: float = 0

    def run(self, total_amount: Decimal) -> None:
        self._total_amount = total_amount
        self._load_settings()
        self._socket_manager.start()
        self._reload_settings_time = self._report_time = time()

        while True:
            self._reload_settings()

            try:
                kline = self._klines_queue.get(timeout=1)
            except Empty:
                pass
            else:
                self._bots[kline.symbol].process(kline)

            self._report()

    def _reload_settings(self) -> None:
        if (time() - self._reload_settings_time) >= self._RELOAD_SETTINGS_INTERVAL:
            self._load_settings()
            self._reload_settings_time = time()

    def _report(self) -> None:
        if (time() - self._report_time) >= self._REPORT_INTERVAL:
            statistics = [bot.statistics for bot in self._bots.values()]
            statistics.sort(key=lambda stat: stat['symbol'])

            for stat in statistics:
                parts = [
                    stat['symbol'],
                    f'FINISHED revenue: {stat["finished_revenue"]:.2f} USDT, trades: {stat["finished_trades"]}',
                    f'OPENED revenue: {stat["opened_revenue"]:.2f} USDT, trades: {stat["opened_trades"]}',
                ]
                if stat['out_of_range']:
                    parts.append('OUT OF RANGE')
                if stat['no_funds']:
                    parts.append('NO FUNDS')

                print(' | '.join(parts))

            self._report_time = time()

    def _load_settings(self) -> None:
        old_symbols = set(self._bots.keys())
        self._load_bot_settings()
        new_symbols = set(self._bots.keys())

        if old_symbols != new_symbols:
            self._socket_manager.close()
            streams = [symbol.lower() + '@kline_1m' for symbol in new_symbols]
            self._socket_manager.start_multiplex_socket(streams, self._process_socket_message)

    def _load_bot_settings(self) -> None:
        bots_settings: List[BotSetting] = self._db_session.query(BotSetting).all()
        assert len(bots_settings) != 0

        for bot_settings in bots_settings:
            symbol = bot_settings.symbol

            if symbol not in self._bots:
                self._bots[symbol] = Bot(symbol, self._get_available_amount, self._api, self._db_session)

            settings = {col.name: getattr(bot_settings, col.name) for col in bot_settings.__table__.columns}
            del settings['id']
            self._bots[symbol].load_settings(**settings)

            self._db_session.expire(bot_settings)

    def _get_available_amount(self) -> Decimal:
        return self._total_amount - sum(bot.investment for bot in self._bots.values())

    def _process_socket_message(self, message: dict) -> None:
        data = message['data']['k']
        kline = Kline(symbol=data['s'],
                      open_time=to_datetime(data['t']),
                      close_time=to_datetime(data['T']),
                      open_price=Decimal(data['o']),
                      close_price=Decimal(data['c']),
                      high_price=Decimal(data['h']),
                      low_price=Decimal(data['l']))
        self._klines_queue.put_nowait(kline)


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('total-amount', type=Decimal)
    args = parser.parse_args()
    total_amount = getattr(args, 'total-amount')

    di = Di()
    runner = BotRunner(di.binance_client, di.binance_api, db_session=sessionmaker(di.db_engine)())
    runner.run(total_amount)
