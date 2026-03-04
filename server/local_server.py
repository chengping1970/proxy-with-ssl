import socket, threading, json, logging
from server.miner_client import MinerClientHandler


class LocalTaskServer(threading.Thread):
    """Local server to handle incoming connections from mining clients"""

    def __init__(self, bind):
        super().__init__(daemon=True)
        h, p = bind.split(":")
        self.addr = (h, int(p))
        self.sock = socket.socket()
        self.sock.bind(self.addr)
        self.sock.listen(100)
        self.clients = set()
        self.miners = []

    def run(self):
        """Accept incoming connections from local mining clients"""
        logging.info(
            f"Local task server starting to accept connections: {self.addr[0]}:{self.addr[1]}"
        )
        while True:
            c, a = self.sock.accept()
            logging.info(f"Received local miner connection: {a}")
            h = MinerClientHandler(c, a, self)
            self.clients.add(h)
            h.start()

    def remove(self, h):
        """Remove a client handler from the active clients set"""
        self.clients.discard(h)

    def push_task(self, task):
        """Push a new mining task to all connected clients"""
        logging.info(f"Pushing task to {len(self.clients)} local clients")
        msg = json.dumps({"jsonrpc": "2.0", "id": 0, "result": task}).encode() + b"\n"
        for c in list(self.clients):
            c.sock.sendall(msg)

    def submit(self, msg, client):
        """Submit work from a local client to an active pool"""
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
