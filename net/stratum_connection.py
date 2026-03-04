import json
import socket
import threading
import logging
from typing import Any, Dict, Callable, Optional
from config.defaults import BUFFER_SIZE, MAX_RECV_BUFFER


class StratumConnection:
    """Handles Stratum protocol connection to a mining pool"""

    def __init__(
        self,
        host: str,
        port: int,
        use_ssl: bool,
        create_socket: Callable[[str, int, bool], socket.socket],
        on_message: Callable[[Dict[str, Any]], None],
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
        self.host: str = host
        self.port: int = port
        self.use_ssl: bool = use_ssl
        self.create_socket: Callable[[str, int, bool], socket.socket] = create_socket
        self.on_message: Callable[[Dict[str, Any]], None] = on_message
        self.on_disconnect: Callable[[str], None] = on_disconnect

        self.sock: Optional[socket.socket] = None
        self.buf: bytes = b""
        self.closed: threading.Event = threading.Event()
        self.lock: threading.Lock = threading.Lock()

    def connect(self) -> None:
        """Establish connection to the mining pool"""
        logging.info(
            f"[conn] connecting to {self.host}:{self.port}, ssl={self.use_ssl}"
        )
        self.sock = self.create_socket(self.host, self.port, self.use_ssl)
        self.closed.clear()
        threading.Thread(target=self._recv_loop, daemon=True).start()
        logging.info("[conn] recv loop started")

    def send(self, obj: Dict[str, Any]) -> None:
        """
        Send a JSON-RPC message to the pool
        
        Args:
            obj: JSON-RPC message object to send
        """
        with self.lock:
            if not self.closed.is_set() and self.sock:
                payload: str = json.dumps(obj)
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
            except:
                pass
            self.on_disconnect(reason)

    def _recv_loop(self) -> None:
        """Receive and process incoming messages from the pool"""
        try:
            while not self.closed.is_set() and self.sock:
                try:
                    data: bytes = self.sock.recv(BUFFER_SIZE)
                    if not data:
                        break
                    self.buf += data
                    if len(self.buf) > MAX_RECV_BUFFER:
                        break
                    while b"\n" in self.buf:
                        line: bytes
                        line, self.buf = self.buf.split(b"\n", 1)
                        if line:
                            decoded: str = line.decode()
                            msg: Dict[str, Any] = json.loads(decoded)
                            logging.info(
                                f"[pool->stratum] id={msg.get('id')} method={msg.get('method')}"
                            )
                            logging.debug(f"[pool->stratum][json] {decoded}")
                            self.on_message(msg)
                except socket.timeout:
                    break
        finally:
            self.close("recv_end")
