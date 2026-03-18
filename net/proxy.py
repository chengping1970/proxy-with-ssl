import socket
import ssl
import socks  # type: ignore
import logging
from typing import Optional, Tuple
from urllib.parse import urlparse


PROXY: Optional[Tuple[str, str, int]] = None


def setup_proxy(url: Optional[str]) -> None:
    """
    Configure upstream proxy settings for outbound connections.

    The proxy URL may specify a SOCKS or HTTP/HTTPS proxy.  Only SOCKS5,
    SOCKS4, HTTP, and HTTPS schemes are understood.  HTTP/HTTPS proxies are
    used via a CONNECT tunnel; SOCKS proxies are handled by the ``PySocks``
    library.

    Args:
        url: Proxy URL in format ``scheme://host:port`` or None for direct
             connection.  Examples:
             ``socks5://127.0.0.1:1080`` or ``http://proxy.example.com:8080``
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
    # handle SOCKS proxies first (original behavior)
    if PROXY and PROXY[0].startswith("socks"):
        logging.debug(
            f"Connecting through SOCKS proxy: {PROXY[1]}:{PROXY[2]} -> {host}:{port}"
        )
        s = socks.socksocket()
        s.set_proxy(
            socks.SOCKS5 if PROXY[0] == "socks5" else socks.SOCKS4,
            PROXY[1],
            PROXY[2],
        )
        sock = s
    # support HTTP/HTTPS CONNECT-style proxying
    elif PROXY and PROXY[0].startswith("http"):
        # open a plain socket to the proxy server
        logging.debug(
            f"Connecting through HTTP proxy: {PROXY[1]}:{PROXY[2]} -> {host}:{port}"
        )
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(30)
        sock.connect((PROXY[1], PROXY[2]))

        # if the proxy itself is accessed over TLS, wrap now
        if PROXY[0] == "https":
            logging.debug(
                f"Enabling SSL for proxy connection: {PROXY[1]}:{PROXY[2]}"
            )
            ctx = ssl.create_default_context()
            sock = ctx.wrap_socket(sock, server_hostname=PROXY[1])

        # issue CONNECT request to establish tunnel
        connect_request = (
            f"CONNECT {host}:{port} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            f"Proxy-Connection: keep-alive\r\n"
            f"\r\n"
        )
        sock.sendall(connect_request.encode())

        # read until end of headers
        response = b""
        while b"\r\n\r\n" not in response:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
        # examine status line
        first_line = response.split(b"\r\n", 1)[0].decode(errors="ignore")
        if "200" not in first_line:
            raise RuntimeError(
                f"HTTP proxy CONNECT failed: {first_line.strip()}"
            )
    else:
        logging.debug(f"Directly connecting to target: {host}:{port}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(30)
        sock.connect((host, port))

    # if the connection was made through a socks proxy or direct socket, wrap
    # with SSL here; for HTTP proxies we also wrap after the CONNECT tunnel is
    # established so the logic can be common
    if use_ssl:
        logging.info(f"Enabling SSL for connection: {host}:{port}")
        ctx = ssl.create_default_context()
        sock = ctx.wrap_socket(sock, server_hostname=host)

    return sock
