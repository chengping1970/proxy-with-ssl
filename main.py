import time
import logging
import signal
import sys
from typing import Any

from utils.args import parse_args
from utils.logger import setup_logger
from net.proxy import setup_proxy, create_socket
from net.stratum_connection import StratumConnection
from server.local_server import LocalTaskServer
from miner.task_pool_miner import TaskPoolMiner


# Global references for cleanup
_server: LocalTaskServer | None = None
_miners: list[TaskPoolMiner] = []
_shutdown_in_progress = False


def parse_pool(p: str) -> tuple[str, int, bool]:
    """
    Parse pool connection string to extract host, port and SSL flag

    Args:
        p: Pool connection string in format [scheme://]host:port

    Returns:
        Tuple of (host, port, ssl_flag)
    """
    if "://" in p:
        scheme, rest = p.split("://", 1)
        scheme = scheme.lower()
        host, port_str = rest.split(":")
        return host, int(port_str), "ssl" in scheme or "tls" in scheme or "tcps" in scheme or "https" in scheme
    host, port_str = p.split(":")
    return host, int(port_str), False


def _cleanup() -> None:
    """Perform graceful shutdown of all components"""
    global _shutdown_in_progress
    if _shutdown_in_progress:
        return
    _shutdown_in_progress = True

    logging.info("Starting graceful shutdown...")

    # Stop miners
    for miner in _miners:
        try:
            miner.stop()
        except Exception as e:
            logging.warning(f"Error stopping miner: {e}")

    # Stop server
    if _server:
        try:
            _server.shutdown()
        except Exception as e:
            logging.warning(f"Error stopping server: {e}")

    logging.info("Graceful shutdown complete")


def signal_handler(signum: int, frame: Any) -> None:
    """
    Handle shutdown signals gracefully

    Args:
        signum: Signal number
        frame: Frame object
    """
    logging.info("Received shutdown signal, cleaning up...")
    _cleanup()
    sys.exit(0)


def main() -> None:
    """Main entry point for the proxy application"""
    global _server, _miners

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    args = parse_args()
    setup_logger(args.log_level)
    logging.debug("Startup arguments parsed, preparing to initialize proxy and local task service")
    setup_proxy(args.proxy)

    _server = LocalTaskServer(args.bind)
    _server.start()
    logging.info(f"Local task service started, listening on: {args.bind}")

    host, port, ssl = parse_pool(args.pool)
    logging.info(f"Pool parsed successfully: host={host}, port={port}, ssl={ssl}")

    workers = (
        args.workers.split(",")
        if args.workers
        else [f"{args.worker_start + i:03d}" for i in range(args.pool_count)]
    )

    _miners = []
    for i, w in enumerate(workers):
        logging.info(
            f"Preparing to start pool connection: pool-{i}, worker={w}, send_task={i == 0}"
        )
        m = TaskPoolMiner(
            f"pool-{i}",
            host,
            port,
            ssl,
            args.username,
            w,
            send_task=(i == 0),
            server=_server,
            create_socket=create_socket,
            StratumConnection=StratumConnection,
        )
        _server.miners.append(m)
        _miners.append(m)
        m.start()

    logging.info(f"All pool threads started, total count: {len(workers)}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Received interrupt signal, shutting down...")
        _cleanup()


if __name__ == "__main__":
    main()
