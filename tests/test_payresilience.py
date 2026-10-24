import pytest
from payresilience import CircuitBreaker, CircuitState, PaymentRouter, PaymentGateway, PaymentInvoice

class MockGateway(PaymentGateway):
    def __init__(self, name: str, should_fail: bool = False):
        super().__init__(name)
        self.should_fail = should_fail

    def _do_create_pix(self, amount_cents: int) -> PaymentInvoice:
        if self.should_fail:
            raise ConnectionError("Gateway timeout")
        return PaymentInvoice("inv_123", amount_cents, "000201...", self.name)

def test_circuit_breaker_transitions():
    cb = CircuitBreaker("test", fail_threshold=2, reset_timeout=0.1)
    assert cb.allow_request()
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert not cb.allow_request()

def test_payment_router_fallback():
    gw1 = MockGateway("gw1", should_fail=True)
    gw2 = MockGateway("gw2", should_fail=False)
    router = PaymentRouter([gw1, gw2])
    
    inv = router.create_invoice(1990)
    assert inv.gateway_used == "gw2"
    assert inv.amount_cents == 1990
