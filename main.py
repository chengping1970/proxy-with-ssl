import time
import logging
import signal
import sys
from utils.args import parse_args
from utils.logger import setup_logger
from net.proxy import setup_proxy, create_socket
from net.stratum_connection import StratumConnection
from server.local_server import LocalTaskServer
from miner.task_pool_miner import TaskPoolMiner


def parse_pool(p):
    """Parse pool connection string to extract host, port and SSL flag"""
    if "://" in p:
        scheme, rest = p.split("://", 1)
        host, port = rest.split(":")
        return host, int(port), scheme.endswith("ssl")
    host, port = p.split(":")
    return host, int(port), False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logging.info("Received shutdown signal, cleaning up...")
    # Perform any cleanup here if needed
    sys.exit(0)


def main():
    """Main entry point for the proxy application"""
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    args = parse_args()
    setup_logger(args.log_level)
    logging.info(
        "Startup arguments parsed, preparing to initialize proxy and local task service"
    )
    setup_proxy(args.proxy)

    server = LocalTaskServer(args.bind)
    server.start()
    logging.info(f"Local task service started, listening on: {args.bind}")

    host, port, ssl = parse_pool(args.pool)
    logging.info(f"Pool parsed successfully: host={host}, port={port}, ssl={ssl}")

    workers = (
        args.workers.split(",")
        if args.workers
        else [f"{args.worker_start + i:03d}" for i in range(args.pool_count)]
    )

    miners = []
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
            server=server,
            create_socket=create_socket,
            StratumConnection=StratumConnection,
        )
        server.miners.append(m)
        miners.append(m)
        m.start()

    logging.info(f"All pool threads started, total count: {len(workers)}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Received interrupt signal, shutting down...")
        # The signal handler will take care of cleanup
        pass


if __name__ == "__main__":
    main()
