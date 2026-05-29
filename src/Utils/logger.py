"""Logger centralizado — un get_logger() por módulo."""
import logging
from src.Config.config import LOG_LEVEL, LOG_FORMAT, LOG_FILE, ensure_dirs


def get_logger(name: str) -> logging.Logger:
    ensure_dirs()
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(LOG_LEVEL)

    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(LOG_LEVEL)
    fh.setFormatter(logging.Formatter(LOG_FORMAT))

    ch = logging.StreamHandler()
    ch.setLevel(LOG_LEVEL)
    ch.setFormatter(logging.Formatter(LOG_FORMAT))

    logger.addHandler(fh)
    logger.addHandler(ch)
    logger.propagate = False
    return logger
