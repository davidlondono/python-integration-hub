from typing import TypedDict


class Customer(TypedDict):
    id: str
    name: str
    email: str


class Invoice(TypedDict):
    id: str
    customer_id: str
    amount_minor: int
    currency: str
    status: str


class Payment(TypedDict):
    id: str
    invoice_id: str
    amount_minor: int
    currency: str
    status: str


CRM_CUSTOMERS: dict[str, dict[str, Customer]] = {
    "acme": {
        "customer_001": {
            "id": "customer_001",
            "name": "Ada Lovelace",
            "email": "ada@acme.example.test",
        }
    },
    "globex": {
        "customer_001": {
            "id": "customer_001",
            "name": "Grace Hopper",
            "email": "grace@globex.example.test",
        }
    },
}
BILLING_CUSTOMERS: dict[str, dict[str, Customer]] = {}
BILLING_INVOICES: dict[str, dict[str, Invoice]] = {
    "acme": {
        "invoice_001": {
            "id": "invoice_001",
            "customer_id": "customer_001",
            "amount_minor": 12500,
            "currency": "USD",
            "status": "open",
        }
    },
    "globex": {
        "invoice_001": {
            "id": "invoice_001",
            "customer_id": "customer_001",
            "amount_minor": 24900,
            "currency": "USD",
            "status": "open",
        }
    },
}
BILLING_PAYMENTS: dict[str, dict[str, Payment]] = {
    "acme": {
        "payment_001": {
            "id": "payment_001",
            "invoice_id": "invoice_001",
            "amount_minor": 12500,
            "currency": "USD",
            "status": "paid",
        }
    },
    "globex": {
        "payment_001": {
            "id": "payment_001",
            "invoice_id": "invoice_001",
            "amount_minor": 24900,
            "currency": "USD",
            "status": "paid",
        }
    },
}
CRM_INVOICES: dict[str, dict[str, Invoice]] = {}
CRM_PAYMENTS: dict[str, dict[str, Payment]] = {}


def get_crm_customer(company_id: str, customer_id: str) -> Customer | None:
    customer = CRM_CUSTOMERS.get(company_id, {}).get(customer_id)
    return dict(customer) if customer else None


def upsert_billing_customer(company_id: str, customer: Customer) -> None:
    BILLING_CUSTOMERS.setdefault(company_id, {})[customer["id"]] = dict(customer)


def get_billing_customer(company_id: str, customer_id: str) -> Customer | None:
    customer = BILLING_CUSTOMERS.get(company_id, {}).get(customer_id)
    return dict(customer) if customer else None


def get_billing_invoice(company_id: str, invoice_id: str) -> Invoice | None:
    invoice = BILLING_INVOICES.get(company_id, {}).get(invoice_id)
    return dict(invoice) if invoice else None


def upsert_crm_invoice(company_id: str, invoice: Invoice) -> None:
    CRM_INVOICES.setdefault(company_id, {})[invoice["id"]] = dict(invoice)


def get_crm_invoice(company_id: str, invoice_id: str) -> Invoice | None:
    invoice = CRM_INVOICES.get(company_id, {}).get(invoice_id)
    return dict(invoice) if invoice else None


def get_billing_payment(company_id: str, payment_id: str) -> Payment | None:
    payment = BILLING_PAYMENTS.get(company_id, {}).get(payment_id)
    return dict(payment) if payment else None


def upsert_crm_payment(company_id: str, payment: Payment) -> None:
    CRM_PAYMENTS.setdefault(company_id, {})[payment["id"]] = dict(payment)


def get_crm_payment(company_id: str, payment_id: str) -> Payment | None:
    payment = CRM_PAYMENTS.get(company_id, {}).get(payment_id)
    return dict(payment) if payment else None
