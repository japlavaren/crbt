import os

from cryptography.utils import cached_property
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from crbt.dto.base import Base


class Di:
    def __init__(self, db_uri: str):
        self._db_uri: str = db_uri

        self._dir = os.path.dirname(os.path.realpath(__file__))
        load_dotenv(f'{self._dir}/../.env')

    @cached_property
    def db_engine(self) -> Engine:
        engine = create_engine(self._db_uri)
        Base.metadata.create_all(engine)

        return engine
