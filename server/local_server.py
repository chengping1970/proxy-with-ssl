import socket
import threading
import json
import logging
from typing import Any
from config.defaults import MAX_BACKLOG


class LocalTaskServer(threading.Thread):
    """Local server to handle incoming connections from mining clients"""

    def __init__(self, bind: str) -> None:
        """
        Initialize local task server

        Args:
            bind: Bind address in format host:port
        """
        super().__init__(daemon=True)
        h, p = bind.split(":")
        self.addr = (h, int(p))
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(self.addr)
        self.sock.listen(MAX_BACKLOG)
        self.clients: set[Any] = set()
        self.miners: list[Any] = []
        self._shutdown = threading.Event()

    def run(self) -> None:
        """Accept incoming connections from local mining clients"""
        logging.debug(
            f"Local task server starting to accept connections: {self.addr[0]}:{self.addr[1]}"
        )
        while not self._shutdown.is_set():
            try:
                self.sock.settimeout(1.0)
                try:
                    c, a = self.sock.accept()
                    logging.info(f"Received local miner connection: {a}")
                    h = MinerClientHandler(c, a, self)
                    self.clients.add(h)
                    h.start()
                except socket.timeout:
                    continue
            except OSError:
                if not self._shutdown.is_set():
                    logging.error("Socket error in accept loop")
                break

    def shutdown(self) -> None:
        """Shutdown the server and close all client connections"""
        logging.info("Shutting down local task server...")
        self._shutdown.set()
        # Close all client connections
        for client in list(self.clients):
            client.close()
        # Close server socket
        try:
            self.sock.close()
        except Exception:
            pass
        logging.info("Local task server shutdown complete")

    def remove(self, h: Any) -> None:
        """
        Remove a client handler from the active clients set

        Args:
            h: Client handler to remove
        """
        self.clients.discard(h)

    def push_task(self, task: list[Any]) -> None:
        """
        Push a new mining task to all connected clients

        Args:
            task: Mining task data to distribute
        """
        if not self.clients:
            return
        logging.info(f"Pushing task to {len(self.clients)} local clients")
        msg = json.dumps({"jsonrpc": "2.0", "id": 0, "result": task}).encode() + b"\n"
        for c in list(self.clients):
            try:
                c.sock.sendall(msg)
            except Exception:
                # Client connection failed, will be cleaned up by handler
                pass

    def submit(self, msg: dict[str, Any], client: Any) -> None:
        """
        Submit work from a local client to an active pool

        Args:
            msg: Submission message from client
            client: Client handler for response callback
        """
        logging.info(
            "Received local client submission, preparing to forward to active pool"
        )
        params = msg["params"]
        rid = msg["id"]

        for m in self.miners:
            if m.state.name == "ACTIVE":
                m.submit_work(params, lambda ok: client.reply(rid, ok))
                return
        client.reply(rid, False)


# Import at end to avoid circular dependency issues
from server.miner_client import MinerClientHandler
