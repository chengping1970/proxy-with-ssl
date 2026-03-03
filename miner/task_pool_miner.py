import threading, time, random, logging
from miner.states import MinerState
from miner.reconnect import ReconnectPolicy
from miner.submit_tracker import SubmitTracker
from config.defaults import HASHRATE_HEARTBEAT_INTERVAL

class TaskPoolMiner(threading.Thread):
    def __init__(self, name, host, port, use_ssl, username, worker,
                 send_task, server, create_socket, StratumConnection):
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
            host, port, use_ssl,
            create_socket,
            self.on_message,
            self.on_disconnect
        )

    def run(self):
        while not self.force_stop:
            try:
                logging.info(f"[{self.name}] 开始连接矿池 {self.conn.host}:{self.conn.port}, ssl={self.conn.use_ssl}")
                self.conn.connect()
                self.state = MinerState.LOGGING_IN
                logging.info(f"[{self.name}] 已连接，发送登录请求")
                self.send_login()

                if not self.login_ack.wait(10):
                    raise TimeoutError("login timeout")

                self.state = MinerState.ACTIVE
                logging.info(f"[{self.name}] 登录成功，进入 ACTIVE 状态")
                self.reconnect.reset()

                threading.Thread(
                    target=self._hashrate_heartbeat,
                    daemon=True
                ).start()

                while self.state == MinerState.ACTIVE:
                    time.sleep(1)

            except Exception as e:
                logging.warning(f"[{self.name}] {e}")

            self.state = MinerState.DISCONNECTED
            delay = self.reconnect.next_delay()
            logging.info(f"[{self.name}] 当前状态 DISCONNECTED，{delay:.2f}s 后重连")
            time.sleep(delay)

    # ---------- protocol ----------

    def send_login(self):
        tag = f"{self.username}.{self.worker}" if self.worker else self.username
        logging.info(f"[{self.name}] 登录标签: {tag}")
        self.conn.send({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_submitLogin",
            "params": [tag, "x"]
        })

    def submit_work(self, params, cb):
        if self.state != MinerState.ACTIVE:
            return
        sid = random.randint(10, 999999)
        logging.info(f"[{self.name}] 转发提交任务 sid={sid}")
        self.submit_tracker.register(sid, cb)
        self.conn.send({
            "jsonrpc": "2.0",
            "id": sid,
            "method": "eth_submitWork",
            "params": params
        })

    def _hashrate_heartbeat(self):
        while self.state == MinerState.ACTIVE:
            try:
                # 0x0 表示 unknown / proxy
                self.conn.send({
                    "jsonrpc": "2.0",
                    "id": random.randint(1000000, 2000000),
                    "method": "eth_submitHashrate",
                    "params": ["0x0", hex(int(time.time()))]
                })
            except:
                pass
            time.sleep(HASHRATE_HEARTBEAT_INTERVAL)

    def on_message(self, msg):
        mid = msg.get("id")
        result = msg.get("result")

        if mid == 1:
            if result is True or isinstance(result, (list, dict)):
                self.login_ack.set()
                if isinstance(result, list) and self.send_task:
                    logging.info(f"[{self.name}] 收到登录附带任务，推送到本地客户端")
                    self.server.push_task(result)
            else:
                raise RuntimeError("login failed")
            return

        if isinstance(mid, int) and mid >= 10:
            logging.info(f"[{self.name}] 收到提交结果 sid={mid}, result={result}")
            self.submit_tracker.resolve(mid, result)
            return

        if isinstance(result, list) and self.send_task:
            logging.info(f"[{self.name}] 收到新任务，推送到本地客户端")
            self.server.push_task(result)

    def on_disconnect(self, reason):
        logging.warning(f"[{self.name}] disconnected: {reason}")
        self.state = MinerState.DISCONNECTED
        self.login_ack.clear()