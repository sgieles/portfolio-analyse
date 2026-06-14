"""Centralised logging configuration for the application."""

import logging
import sys
from pathlib import Path

LOG_FORMAT = "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def setup_logging(level: int = logging.DEBUG, log_file: str | None = "portfolio_analyser.log") -> None:
    """Configure root logger with console + optional file handler.

    Call once at application start-up (main.py). Subsequent calls are no-ops.
    """
    global _configured
    if _configured:
        return
    _configured = True

    root = logging.getLogger()
    root.setLevel(level)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    if log_file:
        log_path = Path(log_file)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger. Import this instead of logging.getLogger directly."""
    return logging.getLogger(name)
