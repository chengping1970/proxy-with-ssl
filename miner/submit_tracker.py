import threading
from typing import Dict, Callable, Any, Optional


class SubmitTracker:
    """Tracks pending work submissions and their callbacks"""
    
    def __init__(self) -> None:
        """Initialize the submit tracker"""
        self.pending: Dict[int, Callable[[Any], None]] = {}
        self.lock: threading.Lock = threading.Lock()

    def register(self, sid: int, cb: Callable[[Any], None]) -> None:
        """
        Register a callback for a submission ID
        
        Args:
            sid: Submission ID
            cb: Callback function to call when result arrives
        """
        with self.lock:
            self.pending[sid] = cb

    def resolve(self, sid: int, result: Any) -> None:
        """
        Resolve a pending submission with its result
        
        Args:
            sid: Submission ID
            result: Result to pass to the callback
        """
        with self.lock:
            cb: Optional[Callable[[Any], None]] = self.pending.pop(sid, None)
        if cb:
            cb(result)