# Development Guide for Agentic Coding Agents

This document provides essential information for AI coding assistants working with this Python-based proxy and mining pool management system.

## Project Structure
```
├── main.py              # Entry point
├── config/
│   └── defaults.py      # Configuration constants
├── miner/               # Mining pool connection logic
├── net/                 # Network communication layer
├── server/              # Local server for client connections
└── utils/               # Helper modules
```

## Build/Lint/Test Commands

### Dependencies
```bash
pip install -r requirements.txt
```

### Running the Application
```bash
# Basic execution
python main.py

# With arguments for specific configuration
python main.py --bind 127.0.0.1:8080 --pool example.com:3333 --username user --worker_start 1 --pool_count 5
```

### Linting & Formatting
We maintain consistent code style through automated tools:
```bash
# Auto-format code (preferred)
black .

# Alternative PEP8 formatter (optional)
autopep8 --in-place --recursive .

# Import sorting (standard library first, then third-party, then local)
isort .
```

### Type Checking
```bash
# Static type analysis
mypy --strict .
```

### Testing
Currently, this project relies on runtime validation rather than formal unit tests. However, when making changes:

```bash
# Verify imports resolve correctly
python -c "import sys; sys.path.append('.'); import main"

# Run with minimal config to test core functionality
python main.py --help
```

### Single Test Execution
There are no formal unit tests. Testing involves:
1. Running the application with real pools/servers
2. Monitoring logs for expected behaviors
3. Verifying network communication through packet captures if needed

## Code Style Guidelines

### Imports
1. Group imports in three sections separated by blank lines:
   ```python
   # Standard library imports
   import socket
   import threading
   
   # Third-party imports
   import requests
   
   # Local application imports
   from net.proxy import setup_proxy
   ```
2. Use explicit imports (`from module import Class`) over wildcard imports
3. Sort imports alphabetically within each group

### Formatting
1. Follow PEP 8 with 4-space indentation (no tabs)
2. Max line length: 88 characters (Black default)
3. Use parentheses for line continuation instead of backslashes
4. Always use trailing commas in multi-line sequences

### Naming Conventions
1. Variables/functions: snake_case (e.g., `parse_pool`, `create_socket`)
2. Classes: PascalCase (e.g., `LocalTaskServer`, `MinerClientHandler`)
3. Constants: UPPER_SNAKE_CASE (e.g., `HASHRATE_HEARTBEAT_INTERVAL`)
4. Private methods: prefixed with underscore (e.g., `_hashrate_heartbeat`)
5. Thread objects: descriptive names reflecting purpose

### Types & Documentation
1. Use type hints for function signatures:
   ```python
   def parse_pool(p: str) -> Tuple[str, int, bool]:
   ```
2. Document all public APIs with docstrings following Sphinx convention
3. Include inline comments for complex logic but avoid redundant comments

### Error Handling
1. Use specific exception types over generic except clauses
2. Always log exceptions at appropriate levels (warning/error/critical)
3. Prefer raising meaningful custom exceptions when necessary
4. Gracefully handle connection timeouts and malformed responses
5. Implement retry policies with exponential backoff for transient errors

### Threading Practices
1. Extend threading.Thread for background processes
2. Use daemon threads for non-critical background tasks
3. Protect shared resources with locks or queues
4. Terminate threads cleanly via flags/events rather than force killing
5. Handle thread lifecycle properly during application shutdown

### Logging Standards
1. Use standard library `logging` module exclusively
2. Log at appropriate severity levels:
   - DEBUG: Diagnostic info for developers
   - INFO: General operational messages
   - WARNING: Recoverable issues requiring attention
   - ERROR: Unrecoverable problems preventing normal operation
3. Format messages clearly with contextual information
4. Avoid sensitive information like passwords in logs
5. Include thread identifiers for multi-threaded operations

### Network Programming Notes
1. Always close sockets using try-finally or context managers
2. Set appropriate timeouts for all blocking operations
3. Handle partial reads/writes appropriately for stream protocols
4. Validate incoming data before processing
5. Secure SSL/TLS connections with certificate verification where applicable

### Performance Considerations
1. Minimize object creation in tight loops
2. Reuse connections where feasible
3. Use efficient data structures for frequent lookups (sets/dicts)
4. Limit memory allocations for high-frequency operations
5. Profile CPU-bound sections if performance becomes critical

### Memory Management
1. Dereference large objects promptly after use
2. Monitor for circular references that prevent garbage collection
3. Close file descriptors explicitly when done
4. Unregister event listeners/callbacks to prevent leaks
5. Use weak references where appropriate for caches/registries

## AI Agent Specific Notes

1. This project handles cryptocurrency mining pool communications - treat all financial-related code with extreme care
2. Pay attention to thread safety in classes extending threading.Thread
3. Be cautious when modifying network protocols; verify compatibility with Ethproxy/Stratum standards
4. Respect rate limits imposed by external mining pools to prevent IP blacklisting
5. Prioritize correctness over cleverness - reliability is paramount in production environments
6. Test edge cases thoroughly, especially around connection failures and malformed inputs
7. Follow existing code patterns closely; consistency matters more than personal preference
8. Document assumptions clearly when they impact system behavior under failure conditions