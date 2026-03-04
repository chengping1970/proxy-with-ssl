import logging
from config.defaults import VALID_LOG_LEVELS


def setup_logger(level: str) -> None:
    """
    Configure logging for the application

    Args:
        level: Logging level as string (debug/info/warning/error/critical)

    Raises:
        ValueError: If the provided log level is invalid
    """
    level_lower = level.lower()
    if level_lower not in VALID_LOG_LEVELS:
        raise ValueError(
            f"Invalid log level: '{level}'. "
            f"Valid levels are: {', '.join(VALID_LOG_LEVELS)}"
        )
    numeric_level: int = getattr(logging, level_lower.upper())
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
