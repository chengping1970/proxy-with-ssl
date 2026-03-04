import json
import threading
import logging
from typing import Any, Dict, TYPE_CHECKING
from config.defaults import BUFFER_SIZE

if TYPE_CHECKING:
    from server.local_server import LocalTaskServer
    import socket


class MinerClientHandler(threading.Thread):
    """Handle individual miner client connections and process their requests"""

    def __init__(self, sock: 'socket.socket', addr: tuple, server: 'LocalTaskServer') -> None:
        """
        Initialize miner client handler
        
        Args:
            sock: Client socket connection
            addr: Client address tuple
            server: Reference to parent server
        """
        super().__init__(daemon=True)
        self.sock: 'socket.socket' = sock
        self.server: 'LocalTaskServer' = server
        self.buf: bytes = b""
        self.alive: bool = True

    def run(self) -> None:
        """Process incoming messages from the miner client"""
        logging.info("MinerClientHandler started")
        try:
            while self.alive:
                data: bytes = self.sock.recv(BUFFER_SIZE)
                if not data:
                    logging.info("Local client disconnected")
                    break
                self.buf += data
                while b"\n" in self.buf:
                    line: bytes
                    line, self.buf = self.buf.split(b"\n", 1)
                    if line:
                        self.handle(json.loads(line.decode()))
        finally:
            logging.info("MinerClientHandler cleaning up connection resources")
            self.alive = False
            self.sock.close()
            self.server.remove(self)

    def handle(self, msg: Dict[str, Any]) -> None:
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
        self.sock.sendall(
            json.dumps({"jsonrpc": "2.0", "id": rid, "result": result}).encode() + b"\n"
        )
