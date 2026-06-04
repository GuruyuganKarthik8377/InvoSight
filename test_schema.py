from models.invoice_schema import build_invoice_schema

cleaned_data = {
    "vendor_name": "ABC",
    "invoice_number": "INV-1",
    "invoice_date": "2024-01-01",
    "currency": "INR",
    "subtotal": 100,
    "tax": 18,
    "total": 118,
    "line_items": [
        {"description": "item", "quantity": 1, "unit_price": 100, "amount": 100}
    ]
}

errors = []
status = "success"
confidence = 0.92

invoice = build_invoice_schema(cleaned_data, errors, status, confidence)

print(invoice.model_dump())
