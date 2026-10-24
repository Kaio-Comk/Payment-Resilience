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

class PaymentGateway:
    def __init__(self, name: str):
        self.name = name
        self.cb = CircuitBreaker(name, fail_threshold=3, reset_timeout=30.0)

    def create_pix(self, amount_cents: int) -> PaymentInvoice:
        if not self.cb.allow_request():
            raise RuntimeError(f"Circuit breaker for gateway {self.name} is OPEN")
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
            if not gw.cb.allow_request():
                continue
            try:
                return gw.create_pix(amount_cents)
            except Exception as e:
                errors.append(f"{gw.name}: {e}")
        raise RuntimeError(f"All payment gateways unavailable. Errors: {'; '.join(errors)}")
