import os
import json

import anthropic
from dotenv import load_dotenv, find_dotenv


# Load from nearest .env walking up from CWD.
load_dotenv(find_dotenv(usecwd=True))

# Fallback: explicitly try the nested project .env path used in this repo.
if not os.getenv("ANTHROPIC_API_KEY"):
    _here = os.path.dirname(os.path.abspath(__file__))
    _root = os.path.abspath(os.path.join(_here, "..", ".."))
    for candidate in (
        os.path.join(_root, ".env"),
        os.path.join(_root, "invoice data extractor", "invoice data extractor", ".env"),
    ):
        if os.path.exists(candidate):
            load_dotenv(candidate, override=False)
            if os.getenv("ANTHROPIC_API_KEY"):
                break

api_key = os.getenv("ANTHROPIC_API_KEY")

if not api_key:
    raise RuntimeError(
        "ANTHROPIC_API_KEY not found. Check your .env file or environment variables."
    )

print("API KEY LOADED:", bool(api_key))

client = anthropic.Anthropic(api_key=api_key)

MAX_TOKENS = 500
MAX_INPUT_CHARS = 3000
TEMPERATURE = 0

# Cached model id — resolved once per process.
MODEL_NAME = None


def get_available_models(client) -> list[str]:
    """Return all model ids visible to the current API key."""
    models = client.models.list()
    return [m.id for m in models.data]


def get_claude4_model(client) -> str:
    """Select a Claude 4 model. Prefer sonnet variants."""
    models = get_available_models(client)

    claude4_models = [m for m in models if "claude" in m.lower() and "4" in m]

    if not claude4_models:
        raise RuntimeError("No supported model for this API key")

    for m in claude4_models:
        if "sonnet" in m.lower():
            return m

    return claude4_models[0]


def _resolve_model() -> str:
    """Lazy, cached lookup so we hit models.list() at most once."""
    global MODEL_NAME
    if MODEL_NAME is None:
        MODEL_NAME = get_claude4_model(client)
        print(f"[INFO] Using Claude model: {MODEL_NAME}")
    return MODEL_NAME

SYSTEM_PROMPT = """You are a strict invoice extraction engine.

Rules:
- Extract values exactly from OCR text when available
- If a field is missing but can be safely derived from line items, compute it
- Never guess unrelated values

Allowed inference:
- If only one line item exists → total = amount
- subtotal = sum of line_items
- tax = total - subtotal (if both exist)

Vendor name must be exact from text.

Return ONLY valid JSON.
No markdown.
No explanation."""

USER_PROMPT_TEMPLATE = """Extract invoice data.

Fields:
- vendor_name (top company name, exact text)
- invoice_number
- invoice_date (YYYY-MM-DD if possible)
- currency
- subtotal
- tax
- total
- line_items (description, quantity, unit_price, amount)

Rules:
- Prefer TABLE DATA over OCR text for line_items and amounts
- Extract amounts from the structured table when available
- Do not ignore numeric columns
- Copy vendor_name exactly from OCR text
- If a field is not present and cannot be safely derived, return null

OCR TEXT:
{RAW_TEXT}

TABLE DATA:
{TABLE_DATA}"""

FALLBACK_JSON = '{"error": "invalid_json"}'


def _call_claude(user_content: str) -> str:
    try:
        response = client.messages.create(
            model=_resolve_model(),
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": user_content,
                }
            ],
        )
        return response.content[0].text
    except Exception:
        return ""


def extract_invoice_fields(raw_text: str, table_text: str = "") -> str:
    # Trim very long OCR to keep Claude latency low.
    if raw_text and len(raw_text) > MAX_INPUT_CHARS:
        raw_text = raw_text[:MAX_INPUT_CHARS]
    if table_text and len(table_text) > MAX_INPUT_CHARS:
        table_text = table_text[:MAX_INPUT_CHARS]
    user_prompt = USER_PROMPT_TEMPLATE.format(
        RAW_TEXT=raw_text or "",
        TABLE_DATA=table_text or "(none)",
    )

    output = _call_claude(user_prompt)

    try:
        json.loads(output)
        return output
    except Exception:
        pass

    correction_prompt = f"""Your previous response was not valid JSON.

Return ONLY valid JSON.
No markdown. No explanation.

OCR TEXT:
{raw_text}"""

    retry_output = _call_claude(correction_prompt)

    try:
        json.loads(retry_output)
        return retry_output
    except Exception:
        return FALLBACK_JSON
