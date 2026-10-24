# 💳 Payment Resilience (payresilience)

### Multi-Gateway Payment Router with Circuit Breakers & Automated Fallback (PIX, Stripe, Stars)

[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg?logo=python&logoColor=white)](https://python.org)
[![Architecture](https://img.shields.io/badge/Pattern-Circuit%20Breaker%20%7C%20Router-orange.svg)](https://github.com/Kaio-Comk/Payment-Resilience)
[![Resilience](https://img.shields.io/badge/Resilience-Zero%20Single%20Point%20of%20Failure-green.svg)](https://github.com/Kaio-Comk/Payment-Resilience)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Never lose a checkout conversion to banking API downtime.**  
*Automatic fallback router with thread-safe Circuit Breaker pattern (CLOSED, OPEN, HALF_OPEN) for PIX, Mercado Pago, EFI, Stripe, and Telegram Payments.*

---

## 🏗️ Architecture

```mermaid
flowchart TD
    Req["🛒 Checkout / Create Invoice"] --> Router["⚖️ Payment Router"]
    
    Router --> Check1{"Primary Gateway (EFI) Healthy?"}
    Check1 -->|CLOSED| GW1["🏦 EFI Gateway API"]
    Check1 -->|OPEN / Timeout| Check2{"Secondary Gateway (Mercado Pago) Healthy?"}
    
    GW1 -->|API Failure (5x)| Trip1["💥 Trip Circuit Breaker to OPEN"]
    Trip1 --> Check2
    
    Check2 -->|CLOSED| GW2["🏦 Mercado Pago Gateway API"]
    Check2 -->|OPEN / Timeout| GW3["⭐ Telegram Stars / Stripe Fallback"]
    
    GW2 & GW3 --> Invoice["📄 Unified PaymentInvoice (QR Code + Copy-Paste)"]
```

---

## 📦 Installation

```bash
pip install git+https://github.com/Kaio-Comk/Payment-Resilience.git
```

---

## 🚀 Quickstart

```python
from payresilience import PaymentRouter, PaymentGateway, PaymentInvoice

class MercadoPagoGateway(PaymentGateway):
    def _do_create_pix(self, amount_cents: int) -> PaymentInvoice:
        # Calls MP API
        return PaymentInvoice("mp_123", amount_cents, "qr_payload", "mercadopago")

class EFIGateway(PaymentGateway):
    def _do_create_pix(self, amount_cents: int) -> PaymentInvoice:
        # Calls EFI API
        return PaymentInvoice("efi_123", amount_cents, "qr_payload", "efi")

router = PaymentRouter([EFIGateway("efi"), MercadoPagoGateway("mp")])
invoice = router.create_invoice(amount_cents=1990)
print(f"Generated QR Code via {invoice.gateway_used}: {invoice.qr_code_payload}")
```

---

## 🛡️ License

MIT License. Extracted and decoupled from the NetHub financial billing core.
