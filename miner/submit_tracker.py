import threading

class SubmitTracker:
    def __init__(self):
        self.pending = {}
        self.lock = threading.Lock()

    def register(self, sid, cb):
        with self.lock:
            self.pending[sid] = cb

    def resolve(self, sid, result):
        with self.lock:
            cb = self.pending.pop(sid, None)
        if cb:
            cb(result)