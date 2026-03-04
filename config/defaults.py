# Configuration constants for the proxy system

# Network buffer sizes
BUFFER_SIZE: int = 1024
MAX_RECV_BUFFER: int = 1024 * 1024
MAX_LINE_LENGTH: int = 64 * 1024

# Mining protocol timing
HASHRATE_HEARTBEAT_INTERVAL: int = 10  # seconds