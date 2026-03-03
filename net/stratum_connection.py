import json, socket, threading, logging
from config.defaults import *

class StratumConnection:
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
        self.sock = self.create_socket(self.host, self.port, self.use_ssl)
        self.closed.clear()
        threading.Thread(target=self._recv_loop, daemon=True).start()

    def send(self, obj):
        with self.lock:
            if not self.closed.is_set():
                self.sock.sendall(json.dumps(obj).encode() + b"\n")

    def close(self, reason):
        if not self.closed.is_set():
            logging.warning(f"[conn] closed: {reason}")
            self.closed.set()
            try:
                self.sock.close()
            except:
                pass
            self.on_disconnect(reason)

    def _recv_loop(self):
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
                            self.on_message(json.loads(line.decode()))
                except socket.timeout:
                    break
        finally:
            self.close("recv_end")