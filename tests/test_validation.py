import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.llm.validation import validate_invoice


def test_validation():
    cases = [
        {"vendor_name": "ABC", "total": 100, "subtotal": 100},
        {"vendor_name": "ABC"},  # missing total
        {"vendor_name": "ABC", "subtotal": 100, "total": 50},  # invalid
        {"vendor_name": "ABC", "total": 100, "invoice_date": "random"},
    ]

    for i, case in enumerate(cases):
        cleaned, errors, status = validate_invoice(case)
        print(f"Case {i}: status={status}, errors={errors}")


if __name__ == "__main__":
    test_validation()
