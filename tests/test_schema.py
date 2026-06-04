import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.invoice_schema import build_invoice_schema


def test_schema():
    cleaned_data = {
        "vendor_name": "ABC",
        "invoice_number": "INV-1",
        "invoice_date": "2024-01-01",
        "currency": "INR",
        "subtotal": 100,
        "tax": 18,
        "total": 118,
        "line_items": [],
    }

    invoice = build_invoice_schema(
        cleaned_data=cleaned_data,
        errors=[],
        status="success",
        confidence=0.9,
    )

    result = invoice.model_dump()
    print(result)

    assert "vendor_name" in result
    assert isinstance(result["total"], (int, float))
    print("PASS: Schema valid")


if __name__ == "__main__":
    test_schema()
