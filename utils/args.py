import argparse
from typing import Any


def parse_args() -> Any:
    """
    Parse command line arguments for the ETC Pool Proxy
    
    Returns:
        Parsed arguments namespace
    """
    p = argparse.ArgumentParser("ETC Pool Proxy")

    p.add_argument(
        "-p", "--pool", required=True, help="Pool address in format host:port"
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
        "-b", "--bind", default="0.0.0.0:9999", help="Local bind address for clients"
    )
    p.add_argument(
        "-x", "--proxy", help="Upstream SOCKS proxy in format socks5://host:port"
    )
    p.add_argument(
        "-l",
        "--log-level",
        default="info",
        help="Logging level (debug/info/warning/error)",
    )

    return p.parse_args()
