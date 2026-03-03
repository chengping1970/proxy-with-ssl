import socket, threading, json
from server.miner_client import MinerClientHandler

class LocalTaskServer(threading.Thread):
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
        while True:
            c, a = self.sock.accept()
            h = MinerClientHandler(c, a, self)
            self.clients.add(h)
            h.start()

    def remove(self, h):
        self.clients.discard(h)

    def push_task(self, task):
        msg = json.dumps({"jsonrpc": "2.0", "id": 0, "result": task}).encode() + b"\n"
        for c in list(self.clients):
            c.sock.sendall(msg)

    def submit(self, msg, client):
        params = msg["params"]
        rid = msg["id"]

        for m in self.miners:
            if m.state.name == "ACTIVE":
                m.submit_work(params, lambda ok: client.reply(rid, ok))
                return
        client.reply(rid, False)