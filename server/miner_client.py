import json, threading, logging
from config.defaults import *


class MinerClientHandler(threading.Thread):
    """Handle individual miner client connections and process their requests"""

    def __init__(self, sock, addr, server):
        super().__init__(daemon=True)
        self.sock = sock
        self.server = server
        self.buf = b""
        self.alive = True

    def run(self):
        """Process incoming messages from the miner client"""
        logging.info("MinerClientHandler started")
        try:
            while self.alive:
                data = self.sock.recv(BUFFER_SIZE)
                if not data:
                    logging.info("Local client disconnected")
                    break
                self.buf += data
                while b"\n" in self.buf:
                    line, self.buf = self.buf.split(b"\n", 1)
                    if line:
                        self.handle(json.loads(line.decode()))
        finally:
            logging.info("MinerClientHandler cleaning up connection resources")
            self.alive = False
            self.sock.close()
            self.server.remove(self)

    def handle(self, msg):
        """Handle incoming JSON-RPC messages from the client"""
        logging.info(f"Received local request method={msg.get('method')}")
        if msg.get("method") == "eth_submitWork":
            self.server.submit(msg, self)
        else:
            self.reply(msg.get("id"), True)

    def reply(self, rid, result):
        """Send a JSON-RPC response back to the client"""
        self.sock.sendall(
            json.dumps({"jsonrpc": "2.0", "id": rid, "result": result}).encode() + b"\n"
        )
