import os

from omotes_sdk import setup_logging, LogLevel

setup_logging(LogLevel.parse(os.environ.get("LOG_LEVEL", "INFO")), "grow_worker")
