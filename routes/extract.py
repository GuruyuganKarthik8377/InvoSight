import os
import time
import tempfile

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel

from services.llm.llm_service import extract_invoice_fields
from services.llm.parser import parse_llm_response
from services.llm.validation import validate_invoice
from models.invoice_schema import build_invoice_schema
from export.export_service import export_excel
from utils.logger import logger


router = APIRouter()


class ExtractRequest(BaseModel):
    raw_text: str
    confidence: float


@router.post("/extract")
def extract_invoice(request: ExtractRequest):
    start_time = time.time()

    # Input safety
    if not request.raw_text or not isinstance(request.raw_text, str) or not request.raw_text.strip():
        logger.warning("Invalid input received")
        raise HTTPException(status_code=400, detail="Invalid input")

    logger.info(
        f"Request received | text_length={len(request.raw_text)} | confidence={request.confidence}"
    )
    logger.info(f"OCR TEXT:\n{request.raw_text[:500]}")

    if request.confidence < 0.6:
        logger.warning(f"Low OCR confidence: {request.confidence}")

    # OCR sanity check
    if len(request.raw_text.strip()) < 20:
        logger.warning("OCR text too short")
        return build_invoice_schema(
            cleaned_data={},
            errors=["ocr_text_too_short"],
            status="failed",
            confidence=request.confidence,
        ).model_dump()

    try:
        # Step 1 — LLM extraction
        try:
            llm_output = extract_invoice_fields(request.raw_text)
        except Exception as e:
            logger.error(f"LLM call failed: {str(e)}")
            elapsed = round((time.time() - start_time) * 1000, 2)
            logger.info(f"Processing time={elapsed}ms")
            return build_invoice_schema(
                cleaned_data={},
                errors=["llm_failure"],
                status="failed",
                confidence=request.confidence,
            ).model_dump()

        logger.info(f"LLM output length={len(llm_output) if llm_output else 0}")
        logger.info(f"LLM OUTPUT:\n{llm_output}")

        # Step 2 — Parse JSON
        try:
            parsed_data = parse_llm_response(llm_output)
        except Exception as e:
            logger.error(f"Parser failed: {str(e)}")
            elapsed = round((time.time() - start_time) * 1000, 2)
            logger.info(f"Processing time={elapsed}ms")
            return build_invoice_schema(
                cleaned_data={},
                errors=["invalid_json"],
                status="failed",
                confidence=request.confidence,
            ).model_dump()

        # Anti-hallucination: total must appear in OCR text
        try:
            total_val = parsed_data.get("total")
            if total_val is not None and str(total_val) not in request.raw_text:
                logger.warning(
                    f"Total value {total_val} not present in OCR text — possible hallucination"
                )
                if isinstance(parsed_data, dict):
                    parsed_data.setdefault("_hallucination_flags", []).append(
                        "total_not_in_ocr"
                    )
        except Exception:
            pass

        # Step 3 — Validation
        try:
            cleaned_data, errors, status = validate_invoice(parsed_data)
            # propagate hallucination flag into errors
            try:
                flags = parsed_data.get("_hallucination_flags") if isinstance(parsed_data, dict) else None
                if flags:
                    errors = list(errors) + flags
                    if status == "success":
                        status = "partial"
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Validation failed: {str(e)}")
            elapsed = round((time.time() - start_time) * 1000, 2)
            logger.info(f"Processing time={elapsed}ms")
            return build_invoice_schema(
                cleaned_data={},
                errors=["validation_failure"],
                status="failed",
                confidence=request.confidence,
            ).model_dump()

        logger.info(f"Validation status={status} | errors={errors}")

        # Step 4 — Schema construction
        invoice = build_invoice_schema(
            cleaned_data=cleaned_data,
            errors=errors,
            status=status,
            confidence=request.confidence,
        )

        elapsed = round((time.time() - start_time) * 1000, 2)
        logger.info(f"Processing time={elapsed}ms")

        return invoice.model_dump()

    except Exception as e:
        logger.critical(f"Unhandled error: {str(e)}")
        elapsed = round((time.time() - start_time) * 1000, 2)
        logger.info(f"Processing time={elapsed}ms")
        return build_invoice_schema(
            cleaned_data={},
            errors=["internal_error"],
            status="failed",
            confidence=request.confidence,
        ).model_dump()


@router.post("/export/excel")
def export_excel_route(request: ExtractRequest):
    try:
        if not request.raw_text or not request.raw_text.strip():
            raise HTTPException(status_code=400, detail="Empty OCR text")

        llm_output = extract_invoice_fields(request.raw_text)
        parsed = parse_llm_response(llm_output)
        cleaned, errors, status = validate_invoice(parsed)

        invoice = build_invoice_schema(
            cleaned,
            errors,
            status,
            request.confidence,
        ).model_dump()

        file_path = export_excel(invoice)
        logger.info(f"Excel exported: {file_path}")

        return FileResponse(
            path=file_path,
            filename="invoice.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Excel export failed")


@router.post("/extract/file")
async def extract_invoice_file(file: UploadFile = File(...)):
    """
    Accept a PDF / PNG / JPG upload.
    - PDF  → fully offline (PyMuPDF + Camelot + regex), no LLM, no network.
    - PNG/JPG → OCR + LLM (network required).
    """
    start_time = time.time()

    suffix = os.path.splitext(file.filename or "")[1].lower()
    if suffix not in {".pdf", ".png", ".jpg", ".jpeg"}:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    # Save upload to a temp file for the pipeline.
    tmp_path = None
    try:
        content = await file.read()
        print("FILE NAME:", file.filename)
        print("FILE SIZE:", len(content))
        if not content:
            raise HTTPException(status_code=400, detail="Empty file upload")

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        logger.info(f"File uploaded: {file.filename} ({len(content)} bytes) -> {tmp_path}")

        # ===== Offline PDF path — no LLM =====
        if suffix == ".pdf":
            print("STEP 1: FILE RECEIVED")
            try:
                from services.ocr.advanced_parser import extract_invoice_from_pdf
                result = extract_invoice_from_pdf(tmp_path)
            except Exception as e:
                print("ERROR:", str(e))
                logger.error(f"Offline PDF extraction failed: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

            elapsed = round((time.time() - start_time) * 1000, 2)
            print(f"TOTAL TIME: {elapsed / 1000:.2f}s")
            logger.info(f"Offline PDF extract | status={result.get('extraction_status')} | items={len(result.get('line_items') or [])} | total={result.get('total')} | time={elapsed}ms")

            result["_ocr_text"] = ""  # not used in offline path; kept for FE compatibility
            return result

        # ----- Layer 1: layout-aware extraction (vector PDFs) -----
        from services.ocr.advanced_parser import (
            extract_text_and_tables,
            parse_tables_to_items,
            compute_total_from_items,
        )

        raw_text = ""
        table_line_items: list = []
        tables_raw: list = []
        confidence = 0.0
        source = "none"

        if suffix == ".pdf":
            adv = extract_text_and_tables(tmp_path)
            raw_text = (adv.get("text") or "").strip()
            tables_raw = adv.get("tables") or []
            table_line_items = parse_tables_to_items(tables_raw)
            if raw_text:
                source = "pymupdf"
                confidence = 0.99  # vector PDF text is authoritative
                logger.info(
                    f"PyMuPDF text len={len(raw_text)} | tables={len(tables_raw)} | items={len(table_line_items)}"
                )

        # ----- Layer 2: OCR fallback (scanned PDFs / images) -----
        if not raw_text:
            try:
                from services.ocr.ocr_service import extract_text
            except Exception as e:
                logger.error(f"OCR import failed: {str(e)}")
                return build_invoice_schema(
                    cleaned_data={},
                    errors=["ocr_unavailable"],
                    status="failed",
                    confidence=0.0,
                ).model_dump()

            ocr_result = extract_text(tmp_path)
            raw_text = ocr_result.get("raw_text", "") or ""
            confidence = float(ocr_result.get("confidence", 0.0) or 0.0)
            source = "ocr"

        print("RAW TEXT RECEIVED:\n", raw_text[:1000])
        logger.info(
            f"source={source} | confidence={confidence} | text_length={len(raw_text)} | table_items={len(table_line_items)}"
        )
        logger.info(f"RAW TEXT:\n{raw_text[:500]}")

        if len(raw_text.strip()) < 20 and not table_line_items:
            logger.warning("Extracted text too short and no tables found")
            return build_invoice_schema(
                cleaned_data={},
                errors=["ocr_text_too_short"],
                status="failed",
                confidence=confidence,
            ).model_dump()

        # Build a compact TABLE DATA string for the LLM prompt
        table_text = ""
        if tables_raw:
            lines = []
            for ti, t in enumerate(tables_raw, 1):
                lines.append(f"--- Table {ti} ---")
                for row in t:
                    lines.append(" | ".join(str(c) for c in row))
            table_text = "\n".join(lines)

        # ---- Pipeline ----
        try:
            llm_output = extract_invoice_fields(raw_text, table_text)
        except Exception as e:
            logger.error(f"LLM call failed: {str(e)}")
            return build_invoice_schema(
                cleaned_data={}, errors=["llm_failure"], status="failed",
                confidence=confidence,
            ).model_dump()

        logger.info(f"LLM OUTPUT:\n{llm_output}")

        try:
            parsed_data = parse_llm_response(llm_output)
        except Exception as e:
            logger.error(f"Parser failed: {str(e)}")
            return build_invoice_schema(
                cleaned_data={}, errors=["invalid_json"], status="failed",
                confidence=confidence,
            ).model_dump()

        # Prefer Camelot-derived line_items + recompute totals deterministically
        if table_line_items:
            parsed_data["line_items"] = table_line_items
            computed = compute_total_from_items(table_line_items)
            if computed > 0:
                parsed_data["subtotal"] = computed
                # Only override total if the LLM didn't return one consistent with the items
                llm_total = parsed_data.get("total")
                if llm_total in (None, 0, "0", ""):
                    parsed_data["total"] = computed
            logger.info(
                f"Overrode line_items with {len(table_line_items)} table rows; computed_subtotal={computed}"
            )

        # Anti-hallucination check (only meaningful for OCR-source data)
        try:
            total_val = parsed_data.get("total")
            if (
                source == "ocr"
                and total_val is not None
                and str(total_val) not in raw_text
                and not table_line_items
            ):
                logger.warning(
                    f"Total value {total_val} not present in OCR text — possible hallucination"
                )
                parsed_data.setdefault("_hallucination_flags", []).append(
                    "total_not_in_ocr"
                )
        except Exception:
            pass

        cleaned, errors, status = validate_invoice(parsed_data)
        flags = parsed_data.get("_hallucination_flags") if isinstance(parsed_data, dict) else None
        if flags:
            errors = list(errors) + flags
            if status == "success":
                status = "partial"

        logger.info(f"Validation status={status} | errors={errors}")

        invoice = build_invoice_schema(
            cleaned_data=cleaned,
            errors=errors,
            status=status,
            confidence=confidence,
        )

        elapsed = round((time.time() - start_time) * 1000, 2)
        logger.info(f"Processing time={elapsed}ms")
        print(f"TOTAL TIME: {elapsed / 1000:.2f}s")

        result = invoice.model_dump()
        result["_ocr_text"] = raw_text  # exposed so the frontend can reuse for export
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.critical(f"Unhandled error in /extract/file: {str(e)}")
        return build_invoice_schema(
            cleaned_data={}, errors=["internal_error"], status="failed", confidence=0.0,
        ).model_dump()
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
