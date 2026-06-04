from services.llm.llm_service import extract_invoice_fields

raw_text = """
ABC Pvt Ltd
Invoice No: INV-123
Date: 2024-01-10
Total: 1200
"""

print(extract_invoice_fields(raw_text))
