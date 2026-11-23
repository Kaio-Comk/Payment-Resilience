"""
Multi-gateway payment router with automatic circuit-breaker fallback.
"""
from dataclasses import dataclass
from .circuit_breaker import CircuitBreaker

@dataclass
class PaymentInvoice:
    invoice_id: str
    amount_cents: int
    qr_code_payload: str
    gateway_used: str

class CircuitOpenError(RuntimeError):
    """The gateway's circuit is open (or its single HALF_OPEN probe is already in flight)."""


class PaymentGateway:
    def __init__(self, name: str, fail_threshold: int = 3, reset_timeout: float = 30.0):
        self.name = name
        self.cb = CircuitBreaker(name, fail_threshold=fail_threshold, reset_timeout=reset_timeout)

    def create_pix(self, amount_cents: int) -> PaymentInvoice:
        # A bad amount is the caller's bug, not a gateway outage: reject it before touching the circuit.
        if isinstance(amount_cents, bool) or not isinstance(amount_cents, int) or amount_cents <= 0:
            raise ValueError(f"amount_cents must be a positive integer, got {amount_cents!r}")
        if not self.cb.allow_request():
            raise CircuitOpenError(f"Circuit breaker for gateway {self.name} is OPEN")
        try:
            inv = self._do_create_pix(amount_cents)
            self.cb.record_success()
            return inv
        except Exception:
            self.cb.record_failure()
            raise

    def _do_create_pix(self, amount_cents: int) -> PaymentInvoice:
        raise NotImplementedError

class PaymentRouter:
    def __init__(self, gateways: list[PaymentGateway]):
        self.gateways = gateways

    def create_invoice(self, amount_cents: int) -> PaymentInvoice:
        errors = []
        for gw in self.gateways:
            # No separate allow_request() here: asking twice would spend the single HALF_OPEN probe
            # and the recovering gateway would never be tried.
            try:
                return gw.create_pix(amount_cents)
            except CircuitOpenError:
                errors.append(f"{gw.name}: circuit open")
            except ValueError:
                raise
            except Exception as e:
                errors.append(f"{gw.name}: {e}")
        raise RuntimeError(f"All payment gateways unavailable. Errors: {'; '.join(errors)}")
