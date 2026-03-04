import json
import socket
import threading
import logging
from typing import Any, Callable
from config.defaults import BUFFER_SIZE, MAX_RECV_BUFFER, CONNECT_TIMEOUT


class StratumConnection:
    """Handles Stratum protocol connection to a mining pool"""

    def __init__(
        self,
        host: str,
        port: int,
        use_ssl: bool,
        create_socket: Callable[[str, int, bool], socket.socket],
        on_message: Callable[[dict[str, Any]], None],
        on_disconnect: Callable[[str], None],
    ) -> None:
        """
        Initialize Stratum connection

        Args:
            host: Pool hostname
            port: Pool port
            use_ssl: Whether to use SSL
            create_socket: Socket creation function
            on_message: Callback for incoming messages
            on_disconnect: Callback for disconnection events
        """
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.create_socket = create_socket
        self.on_message = on_message
        self.on_disconnect = on_disconnect

        self.sock: socket.socket | None = None
        self.buf: bytes = b""
        self.closed = threading.Event()
        self.lock = threading.Lock()
        self._recv_thread: threading.Thread | None = None

    def connect(self) -> None:
        """Establish connection to the mining pool"""
        logging.info(
            f"[conn] connecting to {self.host}:{self.port}, ssl={self.use_ssl}"
        )
        self.sock = self.create_socket(self.host, self.port, self.use_ssl)
        self.sock.settimeout(CONNECT_TIMEOUT)
        self.closed.clear()
        self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._recv_thread.start()
        logging.info("[conn] recv loop started")

    def send(self, obj: dict[str, Any]) -> None:
        """
        Send a JSON-RPC message to the pool

        Args:
            obj: JSON-RPC message object to send
        """
        with self.lock:
            if not self.closed.is_set() and self.sock:
                payload = json.dumps(obj)
                logging.info(
                    f"[stratum->pool] id={obj.get('id')} method={obj.get('method')}"
                )
                logging.debug(f"[stratum->pool][json] {payload}")
                self.sock.sendall(payload.encode() + b"\n")

    def close(self, reason: str) -> None:
        """
        Close the connection to the pool

        Args:
            reason: Reason for closing the connection
        """
        if not self.closed.is_set():
            logging.warning(f"[conn] closed: {reason}")
            self.closed.set()
            try:
                if self.sock:
                    self.sock.close()
            except Exception:
                pass
            self.on_disconnect(reason)

    def _recv_loop(self) -> None:
        """Receive and process incoming messages from the pool"""
        try:
            while not self.closed.is_set() and self.sock:
                try:
                    data = self.sock.recv(BUFFER_SIZE)
                    if not data:
                        self.close("connection_closed_by_peer")
                        return
                    self.buf += data
                    if len(self.buf) > MAX_RECV_BUFFER:
                        self.close("buffer_overflow")
                        return
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
                    # Temporary timeout, continue receiving
                    continue
                except socket.error as e:
                    # Permanent socket error
                    self.close(f"socket_error: {e}")
                    return
        except Exception as e:
            self.close(f"unexpected_error: {e}")
        finally:
            # Ensure cleanup
            if not self.closed.is_set():
                self.close("recv_end")
