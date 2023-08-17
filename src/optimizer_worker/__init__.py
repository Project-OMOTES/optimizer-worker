import os

from nwnsdk import setup_logging, LogLevel

setup_logging(LogLevel.parse(os.environ.get('LOG_LEVEL', 'INFO')), 'optimizer_worker')
