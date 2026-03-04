import random
from typing import Union
from config.defaults import RECONNECT_BASE_DELAY, RECONNECT_MAX_DELAY, RECONNECT_JITTER_RATIO


class ReconnectPolicy:
    """Implements exponential backoff with jitter for connection retries"""

    def __init__(
        self,
        base: Union[int, float] = RECONNECT_BASE_DELAY,
        cap: Union[int, float] = RECONNECT_MAX_DELAY,
    ) -> None:
        """
        Initialize reconnect policy

        Args:
            base: Base delay for exponential backoff
            cap: Maximum delay cap in seconds
        """
        self.base = base
        self.cap = cap
        self.attempt = 0

    def reset(self) -> None:
        """Reset attempt counter to zero"""
        self.attempt = 0

    def next_delay(self) -> float:
        """
        Calculate next delay with exponential backoff and jitter

        Returns:
            Delay in seconds before next connection attempt
        """
        d = min(self.base * (2**self.attempt), self.cap)
        self.attempt += 1
        return d + random.uniform(0, d * RECONNECT_JITTER_RATIO)
