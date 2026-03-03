import time
import logging
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
    logging.info("启动参数已解析，准备初始化代理与本地任务服务")
    setup_proxy(args.proxy)

    server = LocalTaskServer(args.bind)
    server.start()
    logging.info(f"本地任务服务已启动，监听地址: {args.bind}")

    host, port, ssl = parse_pool(args.pool)
    logging.info(f"矿池解析完成: host={host}, port={port}, ssl={ssl}")

    workers = (
        args.workers.split(",")
        if args.workers
        else [f"{args.worker_start+i:03d}" for i in range(args.pool_count)]
    )

    for i, w in enumerate(workers):
        logging.info(f"准备启动矿池连接: pool-{i}, worker={w}, send_task={i == 0}")
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

    logging.info(f"全部矿池线程已启动，共 {len(workers)} 个")

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
