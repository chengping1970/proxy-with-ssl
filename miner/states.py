from enum import Enum


class MinerState(Enum):
    """Enumeration of possible miner connection states

    Attributes:
        DISCONNECTED: Connection is disconnected
        LOGGING_IN: Authentication in progress
        ACTIVE: Connection is active and ready
    """

    DISCONNECTED = "disconnected"
    LOGGING_IN = "logging_in"
    ACTIVE = "active"
