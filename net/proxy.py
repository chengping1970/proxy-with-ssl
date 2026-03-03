import socket, ssl, socks
import logging
from urllib.parse import urlparse

PROXY = None

def setup_proxy(url):
    global PROXY
    if not url:
        logging.info("未配置上游代理，使用直连模式")
        return
    u = urlparse(url)
    PROXY = (u.scheme, u.hostname, u.port)
    logging.info(f"代理配置完成: scheme={u.scheme}, host={u.hostname}, port={u.port}")

def create_socket(host, port, use_ssl):
    if PROXY and PROXY[0].startswith("socks"):
        logging.info(f"通过 SOCKS 代理连接: {PROXY[1]}:{PROXY[2]} -> {host}:{port}")
        s = socks.socksocket()
        s.set_proxy(
            socks.SOCKS5 if PROXY[0] == "socks5" else socks.SOCKS4,
            PROXY[1], PROXY[2]
        )
    else:
        logging.info(f"直连目标地址: {host}:{port}")
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    s.settimeout(30)
    s.connect((host, port))

    if use_ssl:
        logging.info(f"为连接启用 SSL: {host}:{port}")
        ctx = ssl.create_default_context()
        s = ctx.wrap_socket(s, server_hostname=host)

    return s
