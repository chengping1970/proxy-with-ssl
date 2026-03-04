import json, socket, threading, logging
from config.defaults import *


class StratumConnection:
    """Handles Stratum protocol connection to a mining pool"""

    def __init__(self, host, port, use_ssl, create_socket, on_message, on_disconnect):
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.create_socket = create_socket
        self.on_message = on_message
        self.on_disconnect = on_disconnect

        self.sock = None
        self.buf = b""
        self.closed = threading.Event()
        self.lock = threading.Lock()

    def connect(self):
        """Establish connection to the mining pool"""
        logging.info(
            f"[conn] connecting to {self.host}:{self.port}, ssl={self.use_ssl}"
        )
        self.sock = self.create_socket(self.host, self.port, self.use_ssl)
        self.closed.clear()
        threading.Thread(target=self._recv_loop, daemon=True).start()
        logging.info("[conn] recv loop started")

    def send(self, obj):
        """Send a JSON-RPC message to the pool"""
        with self.lock:
            if not self.closed.is_set():
                payload = json.dumps(obj)
                logging.info(
                    f"[stratum->pool] id={obj.get('id')} method={obj.get('method')}"
                )
                logging.debug(f"[stratum->pool][json] {payload}")
                self.sock.sendall(payload.encode() + b"\n")

    def close(self, reason):
        """Close the connection to the pool"""
        if not self.closed.is_set():
            logging.warning(f"[conn] closed: {reason}")
            self.closed.set()
            try:
                self.sock.close()
            except:
                pass
            self.on_disconnect(reason)

    def _recv_loop(self):
        """Receive and process incoming messages from the pool"""
        try:
            while not self.closed.is_set():
                try:
                    data = self.sock.recv(BUFFER_SIZE)
                    if not data:
                        break
                    self.buf += data
                    if len(self.buf) > MAX_RECV_BUFFER:
                        break
                    while b"\n" in self.buf:
                        line, self.buf = self.buf.split(b"\n", 1)
                        if line:
                            decoded = line.decode()
                            msg = json.loads(decoded)
                            logging.info(
                                f"[pool->stratum] id={msg.get('id')} method={msg.get('method')}"
                            )
                            logging.debug(f"[pool->stratum][json] {decoded}")
                            self.on_message(msg)
                except socket.timeout:
                    break
        finally:
            self.close("recv_end")
