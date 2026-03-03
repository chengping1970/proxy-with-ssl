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
        try:
            while self.alive:
                data = self.sock.recv(BUFFER_SIZE)
                if not data:
                    break
                self.buf += data
                while b"\n" in self.buf:
                    line, self.buf = self.buf.split(b"\n", 1)
                    if line:
                        self.handle(json.loads(line.decode()))
        finally:
            self.alive = False
            self.sock.close()
            self.server.remove(self)

    def handle(self, msg):
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