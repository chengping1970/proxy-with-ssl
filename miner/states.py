from enum import Enum


class MinerState(Enum):
    """Enumeration of possible miner connection states"""
    
    DISCONNECTED = "disconnected"
    LOGGING_IN = "logging_in"
    ACTIVE = "active"