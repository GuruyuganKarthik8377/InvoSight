import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.llm.llm_service import extract_invoice_fields


def test_llm():
    raw_text = "ABC Pvt Ltd Invoice No: INV-123 Total: 1200"

    output = extract_invoice_fields(raw_text)

    print("LLM OUTPUT:", output)

    try:
        parsed = json.loads(output)
        assert isinstance(parsed, dict)
        print("PASS: Valid JSON")
    except Exception as e:
        print(f"FAIL: Invalid JSON -> {e}")


if __name__ == "__main__":
    test_llm()
