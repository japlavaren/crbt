from datetime import datetime

TIME_FORMAT = '%Y-%m-%d %H:%M:%S'


def to_datetime(timestamp: int) -> datetime:
    return datetime.fromtimestamp(timestamp / 1000)
