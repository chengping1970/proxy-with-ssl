import json, threading, logging
from config.defaults import *

class MinerClientHandler(threading.Thread):
    def __init__(self, sock, addr, server):
        super().__init__(daemon=True)
        self.sock = sock
        self.server = server
        self.buf = b""
        self.alive = True

    def run(self):
        logging.info("MinerClientHandler 启动")
        try:
            while self.alive:
                data = self.sock.recv(BUFFER_SIZE)
                if not data:
                    logging.info("本地客户端断开连接")
                    break
                self.buf += data
                while b"\n" in self.buf:
                    line, self.buf = self.buf.split(b"\n", 1)
                    if line:
                        self.handle(json.loads(line.decode()))
        finally:
            logging.info("MinerClientHandler 清理连接资源")
            self.alive = False
            self.sock.close()
            self.server.remove(self)

    def handle(self, msg):
        logging.info(f"收到本地请求 method={msg.get('method')}")
        if msg.get("method") == "eth_submitWork":
            self.server.submit(msg, self)
        else:
            self.reply(msg.get("id"), True)

    def reply(self, rid, result):
        self.sock.sendall(json.dumps({
            "jsonrpc": "2.0",
            "id": rid,
            "result": result
        }).encode() + b"\n")