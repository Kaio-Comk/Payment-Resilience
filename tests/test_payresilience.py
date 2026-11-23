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


def test_half_open_libera_uma_unica_sonda():
    import time
    cb = CircuitBreaker("x", fail_threshold=1, reset_timeout=0.05)
    cb.record_failure()
    time.sleep(0.12)
    assert sum(cb.allow_request() for _ in range(50)) == 1      # antes: 50 de 50
    assert cb.state == CircuitState.HALF_OPEN
    cb.record_failure()                                        # sonda falhou: reabre na hora
    assert cb.state == CircuitState.OPEN and not cb.allow_request()
    time.sleep(0.12)
    assert cb.allow_request()
    cb.record_success()
    assert cb.state == CircuitState.CLOSED and cb.allow_request() and cb.allow_request()


def test_half_open_uma_unica_sonda_com_threads_simultaneas(monkeypatch):
    """05/11/2026: 32 threads pedem passagem ao mesmo tempo quando o circuito sai de OPEN; o relogio e fixo
    (nada vence durante o teste), entao o resultado tem de ser exatamente 1 sonda. Limite conhecido: no CPython
    com GIL a corrida nao aparece nem sem a trava; a trava protege o Python sem GIL e mudancas futuras."""
    import threading
    import types
    import payresilience.circuit_breaker as cbmod
    monkeypatch.setattr(cbmod, "time", types.SimpleNamespace(monotonic=lambda: 1000.0))
    cb = CircuitBreaker("x", fail_threshold=1, reset_timeout=60)
    cb.state, cb.last_failure_time = CircuitState.OPEN, 0.0      # aberto ha muito tempo: a proxima vira sonda
    largada = threading.Barrier(32)
    liberados = []

    def pedir():
        largada.wait()
        liberados.append(cb.allow_request())

    threads = [threading.Thread(target=pedir) for _ in range(32)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sum(liberados) == 1 and cb.state == CircuitState.HALF_OPEN


def test_sonda_perdida_e_substituida_apos_o_prazo():
    import time
    cb = CircuitBreaker("x", fail_threshold=1, reset_timeout=0.05)
    cb.record_failure()
    time.sleep(0.12)
    assert cb.allow_request() and not cb.allow_request()       # sonda em voo, sem resposta
    time.sleep(0.12)
    assert cb.allow_request()                                  # nova sonda depois do prazo


def test_roteador_volta_a_usar_o_gateway_recuperado():
    import time
    gw = MockGateway("efi", should_fail=True)
    gw.cb = CircuitBreaker("efi", fail_threshold=1, reset_timeout=0.05)
    reserva = MockGateway("mp")
    router = PaymentRouter([gw, reserva])
    assert router.create_invoice(990).gateway_used == "mp"     # efi falhou e abriu o circuito
    gw.should_fail = False
    time.sleep(0.12)
    assert router.create_invoice(990).gateway_used == "efi"    # a sonda chega ao efi e fecha o circuito
    assert gw.cb.state == CircuitState.CLOSED


def test_valor_invalido_nao_conta_como_falha_do_gateway():
    gw = MockGateway("efi")
    for ruim in (0, -1, 19.9, "1990", True):
        with pytest.raises(ValueError):
            PaymentRouter([gw]).create_invoice(ruim)
    assert gw.cb.failures == 0 and gw.cb.state == CircuitState.CLOSED
