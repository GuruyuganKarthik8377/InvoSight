import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.llm.llm_service import extract_invoice_fields
from services.llm.parser import parse_llm_response
from services.llm.validation import validate_invoice
from models.invoice_schema import build_invoice_schema


def test_pipeline():
    raw_text = """
    ACME Corp
    Invoice No: INV-2024-001
    Date: 12/05/2024
    Item A 2 x 500 = 1000
    Tax: 180
    Total: 1180
    """

    confidence = 0.9

    # Step 1 — LLM
    llm_output = extract_invoice_fields(raw_text)
    print("LLM OUTPUT:", llm_output)

    # Step 2 — Parser
    parsed = parse_llm_response(llm_output)
    print("PARSED:", parsed)

    # Step 3 — Validation
    cleaned, errors, status = validate_invoice(parsed)
    print(f"VALIDATION: status={status}, errors={errors}")

    # Step 4 — Schema
    invoice = build_invoice_schema(cleaned, errors, status, confidence)

    result = invoice.model_dump()
    print("FINAL OUTPUT:", result)

    assert "vendor_name" in result
    assert "total" in result
    assert result["extraction_status"] in ["success", "partial", "failed"]
    print("PASS: Pipeline complete")


if __name__ == "__main__":
    test_pipeline()
