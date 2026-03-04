import threading
import time
import random
import logging
from typing import Any, Dict, List, Optional, Callable, TYPE_CHECKING

from miner.states import MinerState
from miner.reconnect import ReconnectPolicy
from miner.submit_tracker import SubmitTracker
from config.defaults import HASHRATE_HEARTBEAT_INTERVAL

if TYPE_CHECKING:
    from server.local_server import LocalTaskServer
    from net.stratum_connection import StratumConnection


class TaskPoolMiner(threading.Thread):
    """Manages connection to a mining pool and handles task distribution"""

    def __init__(
        self,
        name: str,
        host: str,
        port: int,
        use_ssl: bool,
        username: str,
        worker: str,
        send_task: bool,
        server: 'LocalTaskServer',
        create_socket: Callable[[str, int, bool], Any],
        StratumConnection: Any,  # Type annotation for class constructor
    ) -> None:
        """
        Initialize a TaskPoolMiner instance
        
        Args:
            name: Miner identifier
            host: Pool hostname
            port: Pool port
            use_ssl: Whether to use SSL connection
            username: Mining account username
            worker: Worker name
            send_task: Whether this miner should distribute tasks to clients
            server: Reference to local task server
            create_socket: Socket creation function
            StratumConnection: Stratum connection class
        """
        super().__init__(daemon=True)
        self.name: str = name
        self.username: str = username
        self.worker: str = worker
        self.send_task: bool = send_task
        self.server: 'LocalTaskServer' = server
        self.state: MinerState = MinerState.DISCONNECTED
        self.force_stop: bool = False

        self.login_ack: threading.Event = threading.Event()
        self.reconnect: ReconnectPolicy = ReconnectPolicy()
        self.submit_tracker: SubmitTracker = SubmitTracker()

        self.conn: 'StratumConnection' = StratumConnection(
            host, port, use_ssl, create_socket, self.on_message, self.on_disconnect
        )

    def run(self) -> None:
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
            delay: float = self.reconnect.next_delay()
            logging.info(
                f"[{self.name}] Current state DISCONNECTED, reconnecting in {delay:.2f}s"
            )
            time.sleep(delay)

    # ---------- protocol ----------

    def send_login(self) -> None:
        """Send login request to the mining pool"""
        tag: str = f"{self.username}.{self.worker}" if self.worker else self.username
        logging.info(f"[{self.name}] Login tag: {tag}")
        self.conn.send(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_submitLogin",
                "params": [tag, "x"],
            }
        )

    def submit_work(self, params: List[Any], cb: Callable[[Any], None]) -> None:
        """
        Submit mining work result to the pool
        
        Args:
            params: Work submission parameters
            cb: Callback for result notification
        """
        if self.state != MinerState.ACTIVE:
            return
        sid: int = random.randint(10, 999999)
        logging.info(f"[{self.name}] Forwarding submission task sid={sid}")
        self.submit_tracker.register(sid, cb)
        self.conn.send(
            {"jsonrpc": "2.0", "id": sid, "method": "eth_submitWork", "params": params}
        )

    def _hashrate_heartbeat(self) -> None:
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

    def on_message(self, msg: Dict[str, Any]) -> None:
        """
        Handle incoming messages from the mining pool
        
        Args:
            msg: JSON-RPC message from pool
        """
        mid: Optional[int] = msg.get("id")
        result: Any = msg.get("result")

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

    def on_disconnect(self, reason: str) -> None:
        """
        Handle pool disconnection
        
        Args:
            reason: Disconnection reason
        """
        logging.warning(f"[{self.name}] disconnected: {reason}")
        self.state = MinerState.DISCONNECTED
        self.login_ack.clear()
