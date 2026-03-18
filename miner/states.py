from enum import Enum


class MinerState(Enum):
    """Enumeration of possible miner connection states

    Attributes:
        DISCONNECTED: Connection is disconnected
        LOGIN_IN: Authentication in progress
        ACTIVE: Connection is active and ready
    """

    DISCONNECTED = "disconnected"
    LOGIN_IN = "login_in"
    ACTIVE = "active"
