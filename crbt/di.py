import os

from binance.client import Client
from cryptography.utils import cached_property
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from crbt.api.binance_api import BinanceApi
from crbt.dto.base import Base


class Di:
    def __init__(self):
        self._dir = os.path.dirname(os.path.realpath(__file__))
        load_dotenv(f'{self._dir}/../.env')

    @cached_property
    def db_engine(self) -> Engine:
        engine = create_engine(os.getenv('DB_URI'))
        Base.metadata.create_all(engine)

        return engine

    @cached_property
    def binance_client(self) -> Client:
        return Client(os.getenv('API_KEY'), os.getenv('API_SECRET'))

    @cached_property
    def binance_api(self) -> BinanceApi:
        return BinanceApi(self.binance_client)
