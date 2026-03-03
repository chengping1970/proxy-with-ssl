from enum import Enum

class MinerState(Enum):
    DISCONNECTED = "disconnected"
    LOGGING_IN = "logging_in"
    ACTIVE = "active"