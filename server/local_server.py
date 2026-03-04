import socket
import threading
import json
import logging
from typing import Set, List, Dict, Any, TYPE_CHECKING
from server.miner_client import MinerClientHandler

if TYPE_CHECKING:
    from miner.task_pool_miner import TaskPoolMiner


class LocalTaskServer(threading.Thread):
    """Local server to handle incoming connections from mining clients"""

    def __init__(self, bind: str) -> None:
        """
        Initialize local task server
        
        Args:
            bind: Bind address in format host:port
        """
        super().__init__(daemon=True)
        h: str
        p: str
        h, p = bind.split(":")
        self.addr: tuple = (h, int(p))
        self.sock: socket.socket = socket.socket()
        self.sock.bind(self.addr)
        self.sock.listen(100)
        self.clients: Set[MinerClientHandler] = set()
        self.miners: List['TaskPoolMiner'] = []

    def run(self) -> None:
        """Accept incoming connections from local mining clients"""
        logging.info(
            f"Local task server starting to accept connections: {self.addr[0]}:{self.addr[1]}"
        )
        while True:
            c: socket.socket
            a: tuple
            c, a = self.sock.accept()
            logging.info(f"Received local miner connection: {a}")
            h: MinerClientHandler = MinerClientHandler(c, a, self)
            self.clients.add(h)
            h.start()

    def remove(self, h: MinerClientHandler) -> None:
        """
        Remove a client handler from the active clients set
        
        Args:
            h: Client handler to remove
        """
        self.clients.discard(h)

    def push_task(self, task: List[Any]) -> None:
        """
        Push a new mining task to all connected clients
        
        Args:
            task: Mining task data to distribute
        """
        logging.info(f"Pushing task to {len(self.clients)} local clients")
        msg: bytes = json.dumps({"jsonrpc": "2.0", "id": 0, "result": task}).encode() + b"\n"
        for c in list(self.clients):
            c.sock.sendall(msg)

    def submit(self, msg: Dict[str, Any], client: MinerClientHandler) -> None:
        """
        Submit work from a local client to an active pool
        
        Args:
            msg: Submission message from client
            client: Client handler for response callback
        """
        logging.info(
            "Received local client submission, preparing to forward to active pool"
        )
        params: List[Any] = msg["params"]
        rid: Any = msg["id"]

        for m in self.miners:
            if m.state.name == "ACTIVE":
                m.submit_work(params, lambda ok: client.reply(rid, ok))
                return
        client.reply(rid, False)
