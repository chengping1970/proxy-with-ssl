import argparse
import re
from typing import Any


def validate_port(value: str) -> str:
    """
    Validate port number in host:port format

    Args:
        value: String containing host:port

    Returns:
        The validated value

    Raises:
        argparse.ArgumentTypeError: If port is invalid
    """
    if ":" not in value:
        raise argparse.ArgumentTypeError(
            f"Invalid format '{value}', expected host:port"
        )
    _, port_str = value.rsplit(":", 1)
    try:
        port = int(port_str)
        if port < 1 or port > 65535:
            raise argparse.ArgumentTypeError(
                f"Port must be between 1 and 65535, got {port}"
            )
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid port number: {port_str}")
    return value


def validate_pool(value: str) -> str:
    """
    Validate pool address format

    Args:
        value: Pool address string

    Returns:
        The validated value

    Raises:
        argparse.ArgumentTypeError: If pool address is invalid
    """
    # Support formats: host:port, scheme://host:port
    pattern = r"^(?:(?:https?|ssl|socks[45])://)?[a-zA-Z0-9.-]+:\d+$"
    if not re.match(pattern, value):
        raise argparse.ArgumentTypeError(
            f"Invalid pool format '{value}', expected [scheme://]host:port"
        )
    return value


def parse_args() -> Any:
    """
    Parse command line arguments for the ETC Pool Proxy

    Returns:
        Parsed arguments namespace
    """
    p = argparse.ArgumentParser("ETC Pool Proxy")

    p.add_argument(
        "-p",
        "--pool",
        required=True,
        type=validate_pool,
        help="Pool address in format [scheme://]host:port",
    )
    p.add_argument("-u", "--username", required=True, help="Mining username/account")
    p.add_argument("-w", "--workers", help="Comma-separated list of worker names")
    p.add_argument(
        "-n",
        "--pool-count",
        type=int,
        default=1,
        help="Number of pool connections to create",
    )
    p.add_argument(
        "-s", "--worker-start", type=int, default=1, help="Starting worker ID number"
    )
    p.add_argument(
        "-b",
        "--bind",
        type=validate_port,
        default="0.0.0.0:9999",
        help="Local bind address for clients (host:port)",
    )
    p.add_argument(
        "-x", "--proxy", help="Upstream SOCKS proxy in format socks5://host:port"
    )
    p.add_argument(
        "-l",
        "--log-level",
        default="info",
        help="Logging level (debug/info/warning/error/critical)",
    )

    return p.parse_args()
