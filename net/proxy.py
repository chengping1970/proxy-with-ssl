import socket, ssl, socks
from urllib.parse import urlparse

PROXY = None

def setup_proxy(url):
    global PROXY
    if not url:
        return
    u = urlparse(url)
    PROXY = (u.scheme, u.hostname, u.port)

def create_socket(host, port, use_ssl):
    if PROXY and PROXY[0].startswith("socks"):
        s = socks.socksocket()
        s.set_proxy(
            socks.SOCKS5 if PROXY[0] == "socks5" else socks.SOCKS4,
            PROXY[1], PROXY[2]
        )
    else:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    s.settimeout(30)
    s.connect((host, port))

    if use_ssl:
        ctx = ssl.create_default_context()
        s = ctx.wrap_socket(s, server_hostname=host)

    return s