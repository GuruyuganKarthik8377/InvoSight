"""
Layout-aware extraction:
    PDF -> PyMuPDF text  +  Camelot tables  ->  structured data

Falls back gracefully when:
    - file is not a PDF
    - Camelot/Ghostscript is unavailable
    - PDF is image-only (scanned) -> empty text -> caller should run OCR

Public API:
    extract_text_and_tables(file_path) -> {"text": str, "tables": list[list[list[str]]]}
    parse_tables_to_items(tables)       -> list[dict]
    compute_total_from_items(items)     -> float
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def _try_float(x):
    if x is None:
        return None
    s = str(x).strip()
    if not s:
        return None
    # strip currency symbols and thousand separators
    for ch in ("$", "₹", "€", "£", "Rs.", "Rs", "INR", "USD"):
        s = s.replace(ch, "")
    s = s.replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def _extract_pdf_text(file_path: str) -> str:
    """Return text layer from a vector PDF via PyMuPDF. Empty string on failure."""
    try:
        import fitz  # PyMuPDF
    except Exception as e:
        logger.warning("PyMuPDF unavailable: %s", e)
        return ""

    try:
        doc = fitz.open(file_path)
        chunks = []
        for page in doc:
            chunks.append(page.get_text())
        doc.close()
        return "\n".join(chunks).strip()
    except Exception as e:
        logger.warning("PyMuPDF failed for %s: %s", file_path, e)
        return ""


def _extract_pdf_tables(file_path: str) -> list[list[list[str]]]:
    """Return list of tables (each a list of rows) via Camelot. Empty on failure."""
    try:
        import camelot
    except Exception as e:
        logger.warning("Camelot unavailable: %s", e)
        return []

    out: list[list[list[str]]] = []
    # Camelot has two flavors: 'lattice' (ruled tables) and 'stream' (whitespace).
    for flavor in ("lattice", "stream"):
        try:
            tables = camelot.read_pdf(file_path, pages="all", flavor=flavor)
            for t in tables:
                try:
                    rows = t.df.values.tolist()
                    # Strip whitespace and drop fully-empty rows
                    cleaned = [
                        [str(c).strip() for c in row]
                        for row in rows
                        if any(str(c).strip() for c in row)
                    ]
                    if cleaned:
                        out.append(cleaned)
                except Exception as ie:
                    logger.warning("Camelot row decode failed: %s", ie)
            if out:
                logger.info("Camelot flavor=%s extracted %d tables", flavor, len(out))
                return out
        except Exception as e:
            logger.warning("Camelot %s flavor failed: %s", flavor, e)

    return out


def extract_text_and_tables(file_path: str) -> dict:
    """
    Extract text + tables from a PDF.
    For non-PDF (image) inputs returns empty text/tables (caller should use OCR).
    Never raises.
    """
    result = {"text": "", "tables": []}

    try:
        ext = Path(file_path).suffix.lower()
        if ext != ".pdf" or not os.path.exists(file_path):
            return result

        result["text"] = _extract_pdf_text(file_path)
        result["tables"] = _extract_pdf_tables(file_path)
    except Exception as e:
        logger.error("extract_text_and_tables failed: %s", e)

    return result


# ---------------------------------------------------------------------------
# Table -> line items
# ---------------------------------------------------------------------------

_DESC_KEYWORDS  = ("description", "item", "product", "service", "particulars")
_QTY_KEYWORDS   = ("qty", "quantity", "units", "hrs", "hours")
_PRICE_KEYWORDS = ("price", "rate", "unit price", "cost")
_AMT_KEYWORDS   = ("amount", "total", "subtotal", "line total", "value")


def _detect_columns(header_row: list[str]) -> dict:
    """Return mapping of role -> column index, by header keyword match."""
    mapping: dict[str, int] = {}
    for idx, cell in enumerate(header_row):
        h = str(cell or "").lower().strip()
        if not h:
            continue
        if "description" not in mapping and any(k in h for k in _DESC_KEYWORDS):
            mapping["description"] = idx
        if "quantity" not in mapping and any(k in h for k in _QTY_KEYWORDS):
            mapping["quantity"] = idx
        if "unit_price" not in mapping and any(k in h for k in _PRICE_KEYWORDS):
            mapping["unit_price"] = idx
        if "amount" not in mapping and any(k in h for k in _AMT_KEYWORDS):
            mapping["amount"] = idx
    return mapping


def parse_tables_to_items(tables: list[list[list[str]]]) -> list[dict]:
    """Convert raw table rows into line items."""
    items: list[dict] = []
    if not tables:
        return items

    for table in tables:
        if not table or len(table) < 2:
            continue

        header = table[0]
        cols = _detect_columns(header)

        # If header detection finds nothing, assume positional layout
        # (description, quantity, unit_price, amount).
        if not cols:
            cols = {
                "description": 0,
                "quantity": 1 if len(header) > 1 else None,
                "unit_price": 2 if len(header) > 2 else None,
                "amount": 3 if len(header) > 3 else None,
            }
            cols = {k: v for k, v in cols.items() if v is not None}

        for row in table[1:]:
            if not isinstance(row, list) or not row:
                continue

            def cell(role):
                idx = cols.get(role)
                if idx is None or idx >= len(row):
                    return None
                return row[idx]

            desc = cell("description")
            qty = _try_float(cell("quantity"))
            unit = _try_float(cell("unit_price"))
            amt = _try_float(cell("amount"))

            # Filter rows that contain no numeric content at all
            if desc is None and qty is None and unit is None and amt is None:
                continue
            # Skip totals/subtotal rows (description without quantity/unit_price but with amount)
            desc_str = str(desc or "").lower().strip()
            if desc_str in {"total", "subtotal", "tax", "grand total", "balance due"}:
                continue

            items.append({
                "description": str(desc).strip() if desc else None,
                "quantity": qty,
                "unit_price": unit,
                "amount": amt,
            })

    return items


def compute_total_from_items(items: list[dict]) -> float:
    return float(sum(
        item["amount"] for item in items
        if isinstance(item, dict) and item.get("amount")
    ))


# ---------------------------------------------------------------------------
# Offline regex-based field extraction (no LLM)
# ---------------------------------------------------------------------------

import re
from datetime import datetime


_INVOICE_NO_PATTERNS = [
    r"invoice\s*(?:no\.?|number|#)\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-_/]*)",
    r"\binv[\-#]?\s*([A-Z0-9][A-Z0-9\-_/]*)",
    r"bill\s*(?:no\.?|number|#)\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-_/]*)",
]

_DATE_PATTERNS = [
    r"(?:invoice\s*date|date|dated|issued)\s*[:\-]?\s*([0-9]{1,2}[\-/\.][0-9]{1,2}[\-/\.][0-9]{2,4})",
    r"(?:invoice\s*date|date|dated|issued)\s*[:\-]?\s*([0-9]{4}[\-/\.][0-9]{1,2}[\-/\.][0-9]{1,2})",
    r"(?:invoice\s*date|date|dated|issued)\s*[:\-]?\s*([0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{2,4})",
]

_CURRENCY_MAP = {
    "₹": "INR", "rs.": "INR", "rs": "INR", "inr": "INR",
    "$": "USD", "usd": "USD",
    "€": "EUR", "eur": "EUR",
    "£": "GBP", "gbp": "GBP",
}


def _normalize_date(s: str):
    s = s.strip()
    fmts = [
        "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d",
        "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y",
        "%d-%m-%y", "%d/%m/%y",
        "%m-%d-%Y", "%m/%d/%Y",
        "%d %B %Y", "%d %b %Y",
        "%B %d %Y", "%b %d %Y",
        "%d %B, %Y", "%d %b, %Y",
    ]
    for f in fmts:
        try:
            return datetime.strptime(s, f).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _find_first(patterns, text, flags=re.IGNORECASE):
    for p in patterns:
        m = re.search(p, text, flags)
        if m:
            return m.group(1).strip()
    return None


def _find_amount_label(text: str, labels: list[str]):
    """Find the numeric amount appearing after any of the given labels."""
    for label in labels:
        pat = rf"{label}\s*[:\-]?\s*[A-Z₹$€£]*\s*([0-9][0-9,]*(?:\.[0-9]+)?)"
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            v = _try_float(m.group(1))
            if v is not None:
                return v
    return None


def _detect_currency(text: str):
    low = text.lower()
    for token, code in _CURRENCY_MAP.items():
        if token in low:
            return code
    return None


def _guess_vendor_name(text: str):
    """First non-empty, non-keyword line near the top is usually the vendor."""
    skip_words = (
        "invoice", "tax invoice", "bill", "receipt", "estimate",
        "quotation", "credit note", "debit note",
    )
    for line in text.splitlines()[:15]:
        l = line.strip()
        if not l or len(l) < 3:
            continue
        low = l.lower()
        if any(low.startswith(w) for w in skip_words):
            continue
        if re.match(r"^[\d\W]+$", l):
            continue
        return l
    return None


def extract_invoice_from_pdf(file_path: str) -> dict:
    """
    Fully offline PDF invoice extraction — NO LLM, NO network.

    Returns the same shape as the schema:
        vendor_name, invoice_number, invoice_date, currency,
        subtotal, tax, total, line_items, confidence, extraction_status, errors
    Raises only on truly fatal errors (file unreadable).
    """
    print("STEP 1: FILE RECEIVED ->", file_path)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    print("STEP 2: PARSING PDF")
    parsed = extract_text_and_tables(file_path)
    text = parsed.get("text") or ""
    tables = parsed.get("tables") or []

    print("STEP 3: EXTRACTING TABLES (count={})".format(len(tables)))
    line_items = parse_tables_to_items(tables)

    print("STEP 4: BUILDING RESPONSE")
    errors: list[str] = []

    if not text.strip() and not line_items:
        return {
            "vendor_name": None,
            "invoice_number": None,
            "invoice_date": None,
            "currency": None,
            "subtotal": None,
            "tax": None,
            "total": None,
            "line_items": [],
            "confidence": 0.0,
            "extraction_status": "failed",
            "errors": ["empty_pdf_or_scanned"],
        }

    vendor_name = _guess_vendor_name(text)
    invoice_number = _find_first(_INVOICE_NO_PATTERNS, text)

    raw_date = _find_first(_DATE_PATTERNS, text)
    invoice_date = _normalize_date(raw_date) if raw_date else None
    if raw_date and not invoice_date:
        errors.append("invalid_date")

    currency = _detect_currency(text)

    subtotal = _find_amount_label(text, ["subtotal", "sub total", "sub-total", "net amount", "net total"])
    tax = _find_amount_label(text, ["tax", "gst", "vat", "cgst", "sgst", "igst", "service tax"])
    total = _find_amount_label(text, ["grand total", "total amount", "total due", "balance due", "amount due", "total"])

    # Derive from line items if missing
    if not subtotal and line_items:
        s = compute_total_from_items(line_items)
        if s > 0:
            subtotal = s
    if not total and line_items:
        t = compute_total_from_items(line_items)
        if t > 0:
            total = t
    if not total and subtotal:
        total = subtotal + (tax or 0)

    # Required-field flags
    if not vendor_name:
        errors.append("missing_vendor_name")
    if total is None:
        errors.append("missing_total")
    elif subtotal is not None and total < subtotal:
        errors.append("invalid_total")

    # Status
    if "missing_total" in errors:
        status = "failed"
    elif errors:
        status = "partial"
    else:
        status = "success"

    return {
        "vendor_name": vendor_name,
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
        "currency": currency,
        "subtotal": float(subtotal) if subtotal is not None else None,
        "tax": float(tax) if tax is not None else None,
        "total": float(total) if total is not None else None,
        "line_items": line_items,
        "confidence": 0.99 if status == "success" else (0.7 if status == "partial" else 0.0),
        "extraction_status": status,
        "errors": errors,
    }
