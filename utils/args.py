import argparse

def parse_args():
    p = argparse.ArgumentParser("ETC Pool Proxy")

    p.add_argument("-p", "--pool", required=True)
    p.add_argument("-u", "--username", required=True)
    p.add_argument("-w", "--workers")
    p.add_argument("-n", "--pool-count", type=int, default=1)
    p.add_argument("-s", "--worker-start", type=int, default=1)
    p.add_argument("-b", "--bind", default="0.0.0.0:9999")
    p.add_argument("-x", "--proxy")
    p.add_argument("-l", "--log-level", default="info")

    return p.parse_args()