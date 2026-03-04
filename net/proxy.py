import socket
import ssl
import socks  # type: ignore
import logging
from typing import Optional, Tuple
from urllib.parse import urlparse


PROXY: Optional[Tuple[str, str, int]] = None


def setup_proxy(url: Optional[str]) -> None:
    """
    Configure upstream proxy settings for outbound connections

    Args:
        url: Proxy URL in format scheme://host:port or None for direct connection
    """
    global PROXY
    if not url:
        logging.info("No upstream proxy configured, using direct connection mode")
        return
    u = urlparse(url)
    PROXY = (u.scheme, u.hostname, u.port)
    logging.info(
        f"Proxy configuration completed: scheme={u.scheme}, host={u.hostname}, port={u.port}"
    )


def create_socket(host: str, port: int, use_ssl: bool) -> socket.socket:
    """
    Create and configure a socket connection to a remote host

    Args:
        host: Target hostname
        port: Target port
        use_ssl: Whether to wrap socket with SSL

    Returns:
        Configured socket connection
    """
    sock: socket.socket
    if PROXY and PROXY[0].startswith("socks"):
        logging.info(
            f"Connecting through SOCKS proxy: {PROXY[1]}:{PROXY[2]} -> {host}:{port}"
        )
        s = socks.socksocket()
        s.set_proxy(
            socks.SOCKS5 if PROXY[0] == "socks5" else socks.SOCKS4, PROXY[1], PROXY[2]
        )
        sock = s
    else:
        logging.info(f"Directly connecting to target: {host}:{port}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    sock.settimeout(30)
    sock.connect((host, port))

    if use_ssl:
        logging.info(f"Enabling SSL for connection: {host}:{port}")
        ctx = ssl.create_default_context()
        sock = ctx.wrap_socket(sock, server_hostname=host)

    return sock
