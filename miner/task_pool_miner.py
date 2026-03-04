import threading, time, random, logging
from miner.states import MinerState
from miner.reconnect import ReconnectPolicy
from miner.submit_tracker import SubmitTracker
from config.defaults import HASHRATE_HEARTBEAT_INTERVAL


class TaskPoolMiner(threading.Thread):
    """Manages connection to a mining pool and handles task distribution"""

    def __init__(
        self,
        name,
        host,
        port,
        use_ssl,
        username,
        worker,
        send_task,
        server,
        create_socket,
        StratumConnection,
    ):
        super().__init__(daemon=True)
        self.name = name
        self.username = username
        self.worker = worker
        self.send_task = send_task
        self.server = server
        self.state = MinerState.DISCONNECTED
        self.force_stop = False

        self.login_ack = threading.Event()
        self.reconnect = ReconnectPolicy()
        self.submit_tracker = SubmitTracker()

        self.conn = StratumConnection(
            host, port, use_ssl, create_socket, self.on_message, self.on_disconnect
        )

    def run(self):
        """Main connection loop for the miner - connects, logs in, and maintains connection"""
        while not self.force_stop:
            try:
                logging.info(
                    f"[{self.name}] Connecting to pool {self.conn.host}:{self.conn.port}, ssl={self.conn.use_ssl}"
                )
                self.conn.connect()
                self.state = MinerState.LOGGING_IN
                logging.info(f"[{self.name}] Connected, sending login request")
                self.send_login()

                if not self.login_ack.wait(10):
                    raise TimeoutError("login timeout")

                self.state = MinerState.ACTIVE
                logging.info(f"[{self.name}] Login successful, entering ACTIVE state")
                self.reconnect.reset()

                threading.Thread(target=self._hashrate_heartbeat, daemon=True).start()

                while self.state == MinerState.ACTIVE:
                    time.sleep(1)

            except Exception as e:
                logging.warning(f"[{self.name}] {e}")

            self.state = MinerState.DISCONNECTED
            delay = self.reconnect.next_delay()
            logging.info(
                f"[{self.name}] Current state DISCONNECTED, reconnecting in {delay:.2f}s"
            )
            time.sleep(delay)

    # ---------- protocol ----------

    def send_login(self):
        """Send login request to the mining pool"""
        tag = f"{self.username}.{self.worker}" if self.worker else self.username
        logging.info(f"[{self.name}] Login tag: {tag}")
        self.conn.send(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_submitLogin",
                "params": [tag, "x"],
            }
        )

    def submit_work(self, params, cb):
        """Submit mining work result to the pool"""
        if self.state != MinerState.ACTIVE:
            return
        sid = random.randint(10, 999999)
        logging.info(f"[{self.name}] Forwarding submission task sid={sid}")
        self.submit_tracker.register(sid, cb)
        self.conn.send(
            {"jsonrpc": "2.0", "id": sid, "method": "eth_submitWork", "params": params}
        )

    def _hashrate_heartbeat(self):
        """Send periodic hashrate heartbeat to the pool"""
        while self.state == MinerState.ACTIVE:
            try:
                # 0x0 indicates unknown/proxy
                self.conn.send(
                    {
                        "jsonrpc": "2.0",
                        "id": random.randint(1000000, 2000000),
                        "method": "eth_submitHashrate",
                        "params": ["0x0", hex(int(time.time()))],
                    }
                )
            except:
                pass
            time.sleep(HASHRATE_HEARTBEAT_INTERVAL)

    def on_message(self, msg):
        """Handle incoming messages from the mining pool"""
        mid = msg.get("id")
        result = msg.get("result")

        if mid == 1:
            if result is True or isinstance(result, (list, dict)):
                self.login_ack.set()
                if isinstance(result, list) and self.send_task:
                    logging.info(
                        f"[{self.name}] Received login with task, pushing to local clients"
                    )
                    self.server.push_task(result)
            else:
                raise RuntimeError("login failed")
            return

        if isinstance(mid, int) and mid >= 10:
            logging.info(
                f"[{self.name}] Received submission result sid={mid}, result={result}"
            )
            self.submit_tracker.resolve(mid, result)
            return

        if isinstance(result, list) and self.send_task:
            logging.info(f"[{self.name}] Received new task, pushing to local clients")
            self.server.push_task(result)

    def on_disconnect(self, reason):
        """Handle pool disconnection"""
        logging.warning(f"[{self.name}] disconnected: {reason}")
        self.state = MinerState.DISCONNECTED
        self.login_ack.clear()
