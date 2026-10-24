"""
Resilient Circuit Breaker pattern implementation for banking/payment APIs.
Transitions between CLOSED, OPEN, and HALF_OPEN.
"""
from enum import Enum
import time
import threading

class CircuitState(Enum):
    CLOSED = 1
    OPEN = 2
    HALF_OPEN = 3

class CircuitBreaker:
    def __init__(self, name: str, fail_threshold: int = 5, reset_timeout: float = 60.0):
        self.name = name
        self.fail_threshold = fail_threshold
        self.reset_timeout = reset_timeout
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.last_failure_time = 0.0
        self._lock = threading.Lock()

    def allow_request(self) -> bool:
        with self._lock:
            now = time.time()
            if self.state == CircuitState.OPEN:
                if (now - self.last_failure_time) > self.reset_timeout:
                    self.state = CircuitState.HALF_OPEN
                    return True
                return False
            return True

    def record_success(self) -> None:
        with self._lock:
            self.failures = 0
            self.state = CircuitState.CLOSED

    def record_failure(self) -> None:
        with self._lock:
            self.failures += 1
            self.last_failure_time = time.time()
            if self.failures >= self.fail_threshold:
                self.state = CircuitState.OPEN
