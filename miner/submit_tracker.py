import threading
import time
import logging
from typing import Callable, Any


class SubmitTracker:
    """Tracks pending work submissions and their callbacks with timeout cleanup"""

    def __init__(self) -> None:
        """Initialize the submit tracker with cleanup thread"""
        self.pending: dict[int, tuple[Callable[[Any], None], float]] = {}
        self.lock: threading.Lock = threading.Lock()
        self._stop_cleanup = threading.Event()
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()

    def _cleanup_loop(self) -> None:
        """Periodically remove expired pending submissions"""
        while not self._stop_cleanup.is_set():
            self._cleanup_expired()
            self._stop_cleanup.wait(30)

    def _cleanup_expired(self) -> None:
        """Remove submissions that have exceeded the timeout"""
        now = time.time()
        expired: list[int] = []
        with self.lock:
            for sid, (_, timestamp) in self.pending.items():
                if now - timestamp > 60:
                    expired.append(sid)
            for sid in expired:
                self.pending.pop(sid, None)
                logging.warning(f"[SubmitTracker] Removed expired submission sid={sid}")

    def register(self, sid: int, cb: Callable[[Any], None]) -> None:
        """
        Register a callback for a submission ID

        Args:
            sid: Submission ID
            cb: Callback function to call when result arrives
        """
        with self.lock:
            self.pending[sid] = (cb, time.time())

    def resolve(self, sid: int, result: Any) -> None:
        """
        Resolve a pending submission with its result

        Args:
            sid: Submission ID
            result: Result to pass to the callback
        """
        with self.lock:
            item = self.pending.pop(sid, None)
        if item:
            cb, _ = item
            cb(result)

    def stop(self) -> None:
        """Stop the cleanup thread"""
        self._stop_cleanup.set()
