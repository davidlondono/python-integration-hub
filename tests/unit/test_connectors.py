from integration_hub.connectors.simulated import (
    get_billing_customer,
    get_billing_invoice,
    get_billing_payment,
    get_crm_customer,
    get_crm_invoice,
    get_crm_payment,
    upsert_billing_customer,
    upsert_crm_invoice,
    upsert_crm_payment,
)


def test_customer_moves_from_crm_to_billing_by_company() -> None:
    customer = get_crm_customer("acme", "customer_001")

    assert customer is not None
    upsert_billing_customer("acme", customer)

    assert get_billing_customer("acme", "customer_001") == customer
    assert get_billing_customer("globex", "customer_001") is None


def test_invoice_moves_from_billing_to_crm() -> None:
    invoice = get_billing_invoice("acme", "invoice_001")

    assert invoice is not None
    upsert_crm_invoice("acme", invoice)

    assert get_crm_invoice("acme", "invoice_001") == invoice


def test_payment_moves_from_billing_to_crm() -> None:
    payment = get_billing_payment("acme", "payment_001")

    assert payment is not None
    upsert_crm_payment("acme", payment)

    assert get_crm_payment("acme", "payment_001") == payment
