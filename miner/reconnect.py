import random

class ReconnectPolicy:
    def __init__(self, base=1, cap=30):
        self.base = base
        self.cap = cap
        self.attempt = 0

    def reset(self):
        self.attempt = 0

    def next_delay(self):
        d = min(self.base * (2 ** self.attempt), self.cap)
        self.attempt += 1
        return d + random.uniform(0, d * 0.5)