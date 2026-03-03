import socket, threading, json, logging
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
        logging.info(f"本地任务服务器开始接受连接: {self.addr[0]}:{self.addr[1]}")
        while True:
            c, a = self.sock.accept()
            logging.info(f"接收到本地矿机连接: {a}")
            h = MinerClientHandler(c, a, self)
            self.clients.add(h)
            h.start()

    def remove(self, h):
        self.clients.discard(h)

    def push_task(self, task):
        logging.info(f"向 {len(self.clients)} 个本地客户端推送任务")
        msg = json.dumps({"jsonrpc": "2.0", "id": 0, "result": task}).encode() + b"\n"
        for c in list(self.clients):
            c.sock.sendall(msg)

    def submit(self, msg, client):
        logging.info("收到本地客户端提交，准备转发到活动矿池")
        params = msg["params"]
        rid = msg["id"]

        for m in self.miners:
            if m.state.name == "ACTIVE":
                m.submit_work(params, lambda ok: client.reply(rid, ok))
                return
        client.reply(rid, False)