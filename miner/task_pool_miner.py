import threading
import time
import random
import logging
from typing import Any, Callable

from miner.states import MinerState
from miner.reconnect import ReconnectPolicy
from miner.submit_tracker import SubmitTracker
from config.defaults import (
    HASHRATE_HEARTBEAT_INTERVAL,
    LOGIN_TIMEOUT,
    LOGIN_REQUEST_ID,
    SUBMIT_ID_MIN,
    SUBMIT_ID_MAX,
    HEARTBEAT_ID_MIN,
    HEARTBEAT_ID_MAX,
)


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
        server: Any,  # LocalTaskServer
        create_socket: Callable[[str, int, bool], Any],
        StratumConnection: Any,
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

        # Heartbeat control
        self._heartbeat_stop = threading.Event()
        self._heartbeat_thread: threading.Thread | None = None

    def run(self) -> None:
        """Main connection loop for the miner - connects, logs in, and maintains connection"""
        while not self.force_stop:
            try:
                logging.info(
                    f"[{self.name}] Connecting to pool {self.conn.host}:{self.conn.port}, ssl={self.conn.use_ssl}"
                )
                self.conn.connect()
                self.state = MinerState.LOGIN_IN
                logging.info(f"[{self.name}] Connected, sending login request")
                self.send_login()

                if not self.login_ack.wait(LOGIN_TIMEOUT):
                    raise TimeoutError("login timeout")

                self.state = MinerState.ACTIVE
                logging.info(f"[{self.name}] Login successful, entering ACTIVE state")
                self.reconnect.reset()

                self._start_heartbeat()

                while self.state == MinerState.ACTIVE:
                    time.sleep(1)

            except Exception as e:
                logging.warning(f"[{self.name}] {e}")

            self.state = MinerState.DISCONNECTED
            self._stop_heartbeat()
            delay = self.reconnect.next_delay()
            logging.info(
                f"[{self.name}] Current state DISCONNECTED, reconnecting in {delay:.2f}s"
            )
            time.sleep(delay)

    def _start_heartbeat(self) -> None:
        """Start the hashrate heartbeat thread"""
        self._heartbeat_stop.clear()
        self._heartbeat_thread = threading.Thread(
            target=self._hashrate_heartbeat, daemon=True
        )
        self._heartbeat_thread.start()

    def _stop_heartbeat(self) -> None:
        """Stop the hashrate heartbeat thread"""
        self._heartbeat_stop.set()
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=2)
            self._heartbeat_thread = None

    def stop(self) -> None:
        """Stop the miner gracefully"""
        logging.info(f"[{self.name}] Stopping miner...")
        self.force_stop = True
        self.state = MinerState.DISCONNECTED
        self.login_ack.set()  # Unblock any waiting
        self._stop_heartbeat()
        self.submit_tracker.stop()
        self.conn.close("miner_stopped")

    # ---------- protocol ----------

    def send_login(self) -> None:
        """Send login request to the mining pool"""
        tag = f"{self.username}.{self.worker}" if self.worker else self.username
        logging.info(f"[{self.name}] Login tag: {tag}")
        self.conn.send(
            {
                "jsonrpc": "2.0",
                "id": LOGIN_REQUEST_ID,
                "method": "eth_submitLogin",
                "params": [tag, "x"],
            }
        )

    def submit_work(self, params: list[Any], cb: Callable[[Any], None]) -> None:
        """
        Submit mining work result to the pool

        Args:
            params: Work submission parameters
            cb: Callback for result notification
        """
        if self.state != MinerState.ACTIVE:
            return
        sid = random.randint(SUBMIT_ID_MIN, SUBMIT_ID_MAX)
        logging.info(f"[{self.name}] Forwarding submission task sid={sid}")
        self.submit_tracker.register(sid, cb)
        self.conn.send(
            {"jsonrpc": "2.0", "id": sid, "method": "eth_submitWork", "params": params}
        )

    def _hashrate_heartbeat(self) -> None:
        """Send periodic hashrate heartbeat to the pool"""
        while self.state == MinerState.ACTIVE and not self._heartbeat_stop.is_set():
            try:
                # 0x0 indicates unknown/proxy
                self.conn.send(
                    {
                        "jsonrpc": "2.0",
                        "id": random.randint(HEARTBEAT_ID_MIN, HEARTBEAT_ID_MAX),
                        "method": "eth_submitHashrate",
                        "params": ["0x0", hex(int(time.time()))],
                    }
                )
            except Exception:
                pass
            self._heartbeat_stop.wait(HASHRATE_HEARTBEAT_INTERVAL)

    def on_message(self, msg: dict[str, Any]) -> None:
        """
        Handle incoming messages from the mining pool

        Args:
            msg: JSON-RPC message from pool
        """
        mid = msg.get("id")
        result: Any = msg.get("result")

        if mid == LOGIN_REQUEST_ID:
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

        if isinstance(mid, int) and mid >= SUBMIT_ID_MIN:
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
