import json
import threading
import logging
from typing import Any
from config.defaults import BUFFER_SIZE


class MinerClientHandler(threading.Thread):
    """Handle individual miner client connections and process their requests"""

    def __init__(self, sock: Any, addr: tuple, server: Any) -> None:
        """
        Initialize miner client handler

        Args:
            sock: Client socket connection
            addr: Client address tuple
            server: Reference to parent server
        """
        super().__init__(daemon=True)
        self.sock = sock
        self.server = server
        self.buf: bytes = b""
        self.alive = True
        self._lock = threading.Lock()

    def run(self) -> None:
        """Process incoming messages from the miner client"""
        logging.info("MinerClientHandler started")
        try:
            while self.alive:
                try:
                    self.sock.settimeout(1.0)
                    data = self.sock.recv(BUFFER_SIZE)
                    if not data:
                        logging.info("Local client disconnected")
                        break
                    self.buf += data
                    while b"\n" in self.buf:
                        line, self.buf = self.buf.split(b"\n", 1)
                        if line:
                            self.handle(json.loads(line.decode()))
                except socket.timeout:
                    continue
                except json.JSONDecodeError as e:
                    logging.warning(f"Invalid JSON from client: {e}")
                    continue
        except Exception as e:
            logging.info(f"Client connection error: {e}")
        finally:
            logging.info("MinerClientHandler cleaning up connection resources")
            self._cleanup()

    def _cleanup(self) -> None:
        """Clean up client connection resources"""
        with self._lock:
            if self.alive:
                self.alive = False
                try:
                    self.sock.close()
                except Exception:
                    pass
                self.server.remove(self)

    def close(self) -> None:
        """Close the client connection gracefully"""
        self.alive = False
        self._cleanup()

    def handle(self, msg: dict[str, Any]) -> None:
        """
        Handle incoming JSON-RPC messages from the client

        Args:
            msg: JSON-RPC message from client
        """
        logging.info(f"Received local request method={msg.get('method')}")
        if msg.get("method") == "eth_submitWork":
            self.server.submit(msg, self)
        else:
            self.reply(msg.get("id"), True)

    def reply(self, rid: Any, result: Any) -> None:
        """
        Send a JSON-RPC response back to the client

        Args:
            rid: Request ID
            result: Response result
        """
        try:
            with self._lock:
                if self.alive:
                    self.sock.sendall(
                        json.dumps({"jsonrpc": "2.0", "id": rid, "result": result}).encode() + b"\n"
                    )
        except Exception as e:
            logging.warning(f"Failed to send reply to client: {e}")


# Import socket at module level for exception handling
import socket
