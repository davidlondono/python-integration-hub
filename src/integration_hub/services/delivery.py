from typing import cast

from integration_hub.connectors.simulated import (
    Customer,
    Invoice,
    Payment,
    upsert_billing_customer,
    upsert_crm_invoice,
    upsert_crm_payment,
)
from integration_hub.schemas import (
    CustomerEventData,
    InvoiceEventData,
    PaymentEventData,
)


def deliver_event(
    company_slug: str, source: str, event_type: str, event_data: dict[str, object]
) -> None:
    if (source, event_type) == ("crm", "customer.updated"):
        data = CustomerEventData.model_validate(event_data)
        upsert_billing_customer(company_slug, cast(Customer, data.model_dump()))
        return

    if (source, event_type) == ("billing", "invoice.updated"):
        data = InvoiceEventData.model_validate(event_data)
        upsert_crm_invoice(company_slug, cast(Invoice, data.model_dump()))
        return

    if (source, event_type) == ("billing", "payment.updated"):
        data = PaymentEventData.model_validate(event_data)
        upsert_crm_payment(company_slug, cast(Payment, data.model_dump()))
        return

    raise ValueError("Unsupported simulated event")
