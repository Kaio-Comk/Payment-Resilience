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
    """CLOSED lets everything through; OPEN rejects until `reset_timeout` passes; HALF_OPEN lets exactly
    ONE trial request through (the "probe"): success closes the circuit, failure opens it again.

    Before 04/11/2026 HALF_OPEN let every request through, so a gateway that was just recovering got the
    whole backlog at once. A probe that never reports back is replaced after `reset_timeout`.
    Uses a monotonic clock, so a wall-clock adjustment cannot keep the circuit open or reopen it."""

    def __init__(self, name: str, fail_threshold: int = 5, reset_timeout: float = 60.0):
        self.name = name
        self.fail_threshold = fail_threshold
        self.reset_timeout = reset_timeout
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.last_failure_time = 0.0
        self._probe_started = None  # monotonic time of the probe in flight (HALF_OPEN only)
        self._lock = threading.Lock()

    def allow_request(self) -> bool:
        with self._lock:
            now = time.monotonic()
            if self.state == CircuitState.CLOSED:
                return True
            if self.state == CircuitState.OPEN:
                if (now - self.last_failure_time) <= self.reset_timeout:
                    return False
                self.state = CircuitState.HALF_OPEN
                self._probe_started = now
                return True
            # HALF_OPEN: only one probe at a time (a lost probe is replaced after reset_timeout)
            if self._probe_started is not None and (now - self._probe_started) <= self.reset_timeout:
                return False
            self._probe_started = now
            return True

    def record_success(self) -> None:
        with self._lock:
            self.failures = 0
            self._probe_started = None
            self.state = CircuitState.CLOSED

    def record_failure(self) -> None:
        with self._lock:
            self.failures += 1
            self.last_failure_time = time.monotonic()
            if self.state == CircuitState.HALF_OPEN or self.failures >= self.fail_threshold:
                self.state = CircuitState.OPEN   # a failed probe reopens at once
                self._probe_started = None
