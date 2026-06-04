from services.llm.validation import validate_invoice

cases = [
    # valid case
    {
        "vendor_name": "ABC",
        "total": 100,
        "subtotal": 100,
        "line_items": []
    },

    # missing total
    {
        "vendor_name": "ABC"
    },

    # mismatch subtotal
    {
        "vendor_name": "ABC",
        "subtotal": 100,
        "total": 50
    },

    # bad date
    {
        "vendor_name": "ABC",
        "total": 100,
        "invoice_date": "random_text"
    }
]

for i, case in enumerate(cases):
    cleaned, errors, status = validate_invoice(case)
    print(i, status, errors)
