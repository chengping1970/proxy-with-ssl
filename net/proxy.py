import socket, ssl, socks
import logging
from urllib.parse import urlparse

PROXY = None


def setup_proxy(url):
    """Configure upstream proxy settings for outbound connections"""
    global PROXY
    if not url:
        logging.info("No upstream proxy configured, using direct connection mode")
        return
    u = urlparse(url)
    PROXY = (u.scheme, u.hostname, u.port)
    logging.info(
        f"Proxy configuration completed: scheme={u.scheme}, host={u.hostname}, port={u.port}"
    )


def create_socket(host, port, use_ssl):
    """Create and configure a socket connection to a remote host"""
    if PROXY and PROXY[0].startswith("socks"):
        logging.info(
            f"Connecting through SOCKS proxy: {PROXY[1]}:{PROXY[2]} -> {host}:{port}"
        )
        s = socks.socksocket()
        s.set_proxy(
            socks.SOCKS5 if PROXY[0] == "socks5" else socks.SOCKS4, PROXY[1], PROXY[2]
        )
    else:
        logging.info(f"Directly connecting to target: {host}:{port}")
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    s.settimeout(30)
    s.connect((host, port))

    if use_ssl:
        logging.info(f"Enabling SSL for connection: {host}:{port}")
        ctx = ssl.create_default_context()
        s = ctx.wrap_socket(s, server_hostname=host)

    return s
