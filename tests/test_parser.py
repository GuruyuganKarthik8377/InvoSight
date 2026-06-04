import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.llm.parser import parse_llm_response


def test_parser():
    cases = [
        '```json {"total": 100}```',
        'Result: {"total": 200}',
        '{"total": 300,}',
        'INVALID TEXT',
    ]

    for i, case in enumerate(cases):
        try:
            result = parse_llm_response(case)
            print(f"Case {i}: PASS", result)
        except Exception as e:
            print(f"Case {i}: FAIL -> {e}")


if __name__ == "__main__":
    test_parser()
