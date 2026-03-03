import time
from utils.args import parse_args
from utils.logger import setup_logger
from net.proxy import setup_proxy, create_socket
from net.stratum_connection import StratumConnection
from server.local_server import LocalTaskServer
from miner.task_pool_miner import TaskPoolMiner

def parse_pool(p):
    if "://" in p:
        scheme, rest = p.split("://", 1)
        host, port = rest.split(":")
        return host, int(port), scheme.endswith("ssl")
    host, port = p.split(":")
    return host, int(port), False

def main():
    args = parse_args()
    setup_logger(args.log_level)
    setup_proxy(args.proxy)

    server = LocalTaskServer(args.bind)
    server.start()

    host, port, ssl = parse_pool(args.pool)

    workers = (
        args.workers.split(",")
        if args.workers
        else [f"{args.worker_start+i:03d}" for i in range(args.pool_count)]
    )

    for i, w in enumerate(workers):
        m = TaskPoolMiner(
            f"pool-{i}", host, port, ssl,
            args.username, w,
            send_task=(i == 0),
            server=server,
            create_socket=create_socket,
            StratumConnection=StratumConnection
        )
        server.miners.append(m)
        m.start()

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()