import logging
import sys
from app.config.settings import settings

def setup_logger(name: str = "tradeflow") -> logging.Logger:
    """
    Configures and returns a standardized logger outputting to console (stdout)
    and a backend log file. Log level is loaded from system settings.
    """
    logger = logging.getLogger(name)
    
    if logger.hasHandlers():
        logger.handlers.clear()

    # Determine log level
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(log_level)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d) - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler
    file_handler = logging.FileHandler("tradeflow.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.propagate = False
    return logger

logger = setup_logger()
