# Configuration constants for the proxy system

# Network buffer sizes
BUFFER_SIZE: int = 1024
MAX_RECV_BUFFER: int = 1024 * 1024
MAX_LINE_LENGTH: int = 64 * 1024

# Mining protocol timing
HASHRATE_HEARTBEAT_INTERVAL: int = 10  # seconds

# Connection timeouts
CONNECT_TIMEOUT: int = 30  # seconds
LOGIN_TIMEOUT: int = 10  # seconds

# Reconnect policy
RECONNECT_BASE_DELAY: float = 1.0  # seconds
RECONNECT_MAX_DELAY: float = 30.0  # seconds
RECONNECT_JITTER_RATIO: float = 0.5  # 50% jitter

# Submit tracker
SUBMIT_CALLBACK_TIMEOUT: int = 60  # seconds
SUBMIT_CLEANUP_INTERVAL: int = 30  # seconds

# Server settings
DEFAULT_BIND_PORT: int = 9999
MAX_BACKLOG: int = 100

# ID ranges for JSON-RPC
LOGIN_REQUEST_ID: int = 1
SUBMIT_ID_MIN: int = 10
SUBMIT_ID_MAX: int = 999999
HEARTBEAT_ID_MIN: int = 1000000
HEARTBEAT_ID_MAX: int = 2000000

# Valid log levels
VALID_LOG_LEVELS: list[str] = ["debug", "info", "warning", "error", "critical"]