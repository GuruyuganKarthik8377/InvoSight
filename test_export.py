from export.export_service import export_json, export_excel

sample_data = {
    "vendor_name": "ABC",
    "invoice_number": "INV-1",
    "invoice_date": "2024-01-01",
    "currency": "INR",
    "subtotal": 100,
    "tax": 18,
    "total": 118,
    "line_items": [
        {"description": "item", "quantity": 1, "unit_price": 100, "amount": 100}
    ],
    "confidence": 0.9,
    "extraction_status": "success",
    "errors": []
}

json_path = export_json(sample_data)
excel_path = export_excel(sample_data)

print("JSON:", json_path)
print("Excel:", excel_path)
