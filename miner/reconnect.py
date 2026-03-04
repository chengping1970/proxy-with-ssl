import random
from typing import Union


class ReconnectPolicy:
    """Implements exponential backoff with jitter for connection retries"""
    
    def __init__(self, base: Union[int, float] = 1, cap: Union[int, float] = 30) -> None:
        """
        Initialize reconnect policy
        
        Args:
            base: Base delay for exponential backoff
            cap: Maximum delay cap in seconds
        """
        self.base: Union[int, float] = base
        self.cap: Union[int, float] = cap
        self.attempt: int = 0

    def reset(self) -> None:
        """Reset attempt counter to zero"""
        self.attempt = 0

    def next_delay(self) -> float:
        """
        Calculate next delay with exponential backoff and jitter
        
        Returns:
            Delay in seconds before next connection attempt
        """
        d = min(self.base * (2 ** self.attempt), self.cap)
        self.attempt += 1
        return d + random.uniform(0, d * 0.5)