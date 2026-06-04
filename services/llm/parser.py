import re
import json


def parse_llm_response(raw_output: str) -> dict:
    if not raw_output or not isinstance(raw_output, str):
        raise ValueError("Invalid input")

    # STEP 1 — Remove markdown fences
    cleaned = re.sub(
        r"```.*?```",
        lambda m: m.group(0).replace("```json", "").replace("```", ""),
        raw_output,
        flags=re.DOTALL,
    )

    # STEP 2 — Extract JSON substring
    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start == -1 or end == -1:
        raise ValueError("No JSON found")

    json_str = cleaned[start:end + 1]

    # STEP 3 — Remove trailing commas
    json_str = re.sub(r",\s*}", "}", json_str)
    json_str = re.sub(r",\s*]", "]", json_str)

    # STEP 4 — Parse safely
    try:
        parsed = json.loads(json_str)
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON after cleaning")

    # STEP 5 — Enforce dict output
    if not isinstance(parsed, dict):
        raise ValueError("Parsed output is not a dictionary")

    return parsed
