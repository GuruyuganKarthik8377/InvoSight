from services.llm.parser import parse_llm_response

cases = [
    """```json
    {"vendor_name": "ABC"}
    ```""",

    """Here is your result:
    {"total": 1200}
    Thank you""",

    """{"vendor_name": "XYZ",}""",

    """INVALID TEXT"""
]

for i, case in enumerate(cases):
    try:
        result = parse_llm_response(case)
        print(f"Case {i}: PASS", result)
    except Exception as e:
        print(f"Case {i}: FAIL -> {e}")
