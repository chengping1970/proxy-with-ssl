import logging
from typing import Any


def setup_logger(level: str) -> None:
    """
    Configure logging for the application
    
    Args:
        level: Logging level as string (debug/info/warning/error)
    """
    numeric_level: int = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )