from dateutil.parser import parse


def to_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_date(date_str):
    if not date_str:
        return None
    try:
        return parse(str(date_str)).strftime("%Y-%m-%d")
    except (ValueError, TypeError, OverflowError):
        return None


def apply_fallbacks(data: dict) -> dict:
    """Safely derive missing totals/subtotal from line_items."""
    if not isinstance(data, dict):
        return data

    line_items = data.get("line_items") or []
    if not isinstance(line_items, list):
        return data

    items_sum = 0.0
    have_any = False
    for item in line_items:
        if isinstance(item, dict):
            amt = to_float(item.get("amount"))
            if amt is not None:
                items_sum += amt
                have_any = True

    # subtotal fallback: sum of amounts
    if data.get("subtotal") in (None, 0, "0", "") and have_any and items_sum > 0:
        data["subtotal"] = items_sum

    # total fallback: sum of amounts (or single line item amount)
    if data.get("total") in (None, 0, "0", "") and have_any and items_sum > 0:
        data["total"] = items_sum

    return data


def validate_invoice(data: dict) -> tuple[dict, list[str], str]:
    errors: list[str] = []

    if not isinstance(data, dict):
        data = {}

    # --- Apply safe fallbacks before any numeric checks ---
    data = apply_fallbacks(data)

    # --- Numeric normalization (top-level) ---
    subtotal = to_float(data.get("subtotal"))
    tax = to_float(data.get("tax"))
    total = to_float(data.get("total"))

    # --- Date normalization ---
    raw_date = data.get("invoice_date")
    normalized_date = normalize_date(raw_date) if raw_date else None
    if raw_date and normalized_date is None:
        errors.append("invalid_date")

    # --- Line items normalization ---
    raw_line_items = data.get("line_items")
    cleaned_items: list[dict] = []

    if raw_line_items is None:
        cleaned_items = []
    elif not isinstance(raw_line_items, list):
        cleaned_items = []
        errors.append("invalid_line_items")
    else:
        for item in raw_line_items:
            if not isinstance(item, dict):
                errors.append("invalid_line_items")
                continue
            cleaned_items.append({
                "description": item.get("description"),
                "quantity": to_float(item.get("quantity")),
                "unit_price": to_float(item.get("unit_price")),
                "amount": to_float(item.get("amount")),
            })

    # --- Required field checks ---
    if not data.get("vendor_name"):
        errors.append("missing_vendor_name")

    if total is None:
        errors.append("missing_total")
    elif subtotal is not None and total < subtotal:
        errors.append("invalid_total")

    # --- Negative value checks ---
    if subtotal is not None and subtotal < 0:
        errors.append("negative_subtotal")
    if tax is not None and tax < 0:
        errors.append("negative_tax")
    if total is not None and total < 0:
        errors.append("negative_total")
    for idx, item in enumerate(cleaned_items):
        for key in ("quantity", "unit_price", "amount"):
            v = item.get(key)
            if v is not None and v < 0:
                errors.append(f"negative_line_item_{key}")
                break

    # --- Total consistency ---
    if subtotal is not None and total is not None:
        if total < subtotal:
            errors.append("total_less_than_subtotal")

    # --- Line item sum check ---
    if subtotal is not None and cleaned_items:
        sum_items = sum(
            item["amount"] for item in cleaned_items if item.get("amount") is not None
        )
        if subtotal != 0 and abs(sum_items - subtotal) > (0.01 * abs(subtotal)):
            errors.append("line_items_mismatch")

    # --- Cleaned output ---
    cleaned = {
        "vendor_name": data.get("vendor_name"),
        "invoice_number": data.get("invoice_number"),
        "invoice_date": normalized_date,
        "currency": data.get("currency"),
        "subtotal": subtotal,
        "tax": tax,
        "total": total,
        "line_items": cleaned_items,
    }

    # --- Status classification ---
    if "missing_total" in errors:
        status = "failed"
    elif len(errors) == 0:
        status = "success"
    else:
        status = "partial"

    return cleaned, errors, status
