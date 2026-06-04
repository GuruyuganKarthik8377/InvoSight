"""
OCR Service — dual-engine pipeline (PaddleOCR → EasyOCR fallback).

OUTPUT CONTRACT (strict, never changes):
    {
        "raw_text":  str,    # full extracted text; "" on failure
        "confidence": float  # 0.0–1.0; 0.0 on failure
    }
Exactly 2 keys. Never raises exceptions.
"""
import os
import time
import logging
import logging.handlers
import warnings
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# Suppress all C++ / deprecation noise from paddle / torch
os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("FLAGS_enable_pir_api", "0")
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
warnings.filterwarnings("ignore")

import numpy as np
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
_LOG_DIR = os.getenv("LOG_DIR", "./logs")
os.makedirs(_LOG_DIR, exist_ok=True)

_handler = logging.handlers.RotatingFileHandler(
    os.path.join(_LOG_DIR, "ocr.log"),
    maxBytes=10 * 1024 * 1024, backupCount=3, encoding="utf-8"
)
_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s - %(message)s",
                      datefmt="%Y-%m-%d %H:%M:%S")
)
logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger().addHandler(_handler)

_console = logging.StreamHandler()
_console.setLevel(logging.INFO)
_console.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
logging.getLogger().addHandler(_console)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Local imports
# ---------------------------------------------------------------------------
from services.ocr.pdf_loader import load_pdf
from services.ocr.preprocessing import preprocess_image
from services.ocr.utils import pil_to_numpy

_OCR_LANG              = os.getenv("OCR_LANG", "en")
_CONFIDENCE_LOW_PAGE   = 0.65
_CONFIDENCE_SHARPEN_TH = 0.70

# ---------------------------------------------------------------------------
# Engine state — module-level flag controls primary engine
# ---------------------------------------------------------------------------
_USE_PADDLE  = True   # set False permanently after first Paddle failure
_paddle_ocr  = None   # lazy-initialised singleton
_easyocr_reader = None  # lazy-initialised singleton


def _get_paddle():
    """Return a cached PaddleOCR instance, or None if unavailable."""
    global _paddle_ocr
    if _paddle_ocr is not None:
        return _paddle_ocr
    try:
        from paddleocr import PaddleOCR
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            _paddle_ocr = PaddleOCR(lang=_OCR_LANG, use_textline_orientation=True)
        logger.info("[INFO] PaddleOCR engine ready")
    except Exception as exc:
        logger.warning("[WARNING] PaddleOCR unavailable: %s — will use EasyOCR", exc)
        _paddle_ocr = None
    return _paddle_ocr


def _get_easyocr():
    """Return a cached EasyOCR Reader instance."""
    global _easyocr_reader
    if _easyocr_reader is not None:
        return _easyocr_reader
    import easyocr
    _easyocr_reader = easyocr.Reader([_OCR_LANG], gpu=False, verbose=False)
    logger.info("[INFO] EasyOCR engine ready")
    return _easyocr_reader


# ---------------------------------------------------------------------------
# Engine runners
# ---------------------------------------------------------------------------

def run_paddle(image: np.ndarray) -> tuple:
    """
    Run PaddleOCR on a numpy BGR image.
    Returns (texts: list[str], scores: list[float]).
    Raises on any failure so the safe wrapper can catch it.
    """
    raise Exception("force failure")

    if not results:
        return [], []

    texts, scores = [], []
    for item in results:
        if item is None:
            continue
        # PaddleOCR 3.x result is dict-like — access via .get() or attribute
        if hasattr(item, "get"):
            t_list = item.get("rec_texts") or item.get("texts") or []
            s_list = item.get("rec_scores") or item.get("scores") or []
        elif hasattr(item, "rec_texts"):
            t_list = item.rec_texts or []
            s_list = item.rec_scores or []
        elif isinstance(item, (list, tuple)):
            # 2.x legacy format: [[box, (text, score)], ...]
            t_list = [line[1][0] for line in item if line]
            s_list = [float(line[1][1]) for line in item if line]
        else:
            t_list, s_list = [], []

        for t, s in zip(t_list, s_list):
            if t and str(t).strip():
                texts.append(str(t).strip())
                try:
                    scores.append(float(s))
                except (TypeError, ValueError):
                    scores.append(0.0)

    return texts, scores


def run_easyocr(image: np.ndarray) -> tuple:
    """
    Run EasyOCR on a numpy image (RGB or BGR).
    Returns (texts: list[str], scores: list[float]).
    """
    reader  = _get_easyocr()
    results = reader.readtext(image, detail=1, paragraph=False)
    texts   = [r[1] for r in results if r[1].strip()]
    scores  = [float(r[2]) for r in results if r[1].strip()]
    return texts, scores


def run_ocr_safe(image: np.ndarray) -> tuple:
    """
    Dual-engine wrapper.
    1. Try PaddleOCR
    2. On ANY error → permanently switch to EasyOCR for this session
    Returns (texts: list[str], scores: list[float]).
    """
    global _USE_PADDLE

    if _USE_PADDLE:
        try:
            texts, scores = run_paddle(image)
            if texts:
                return texts, scores
            # Empty result — try EasyOCR before giving up
        except Exception as exc:
            logger.warning(
                "[WARNING] PaddleOCR failed (%s) — switching to EasyOCR permanently",
                exc
            )
            _USE_PADDLE = False

    # EasyOCR path
    try:
        return run_easyocr(image)
    except Exception as exc:
        logger.error("[ERROR] EasyOCR also failed: %s", exc)
        return [], []


# ---------------------------------------------------------------------------
# Per-page OCR with preprocessing comparison
# ---------------------------------------------------------------------------

def run_ocr_on_image(image: np.ndarray) -> dict:
    """
    Run the dual-engine OCR on one image.
    Returns {"text": str, "confidence": float}.
    """
    texts, scores = run_ocr_safe(image)

    if not texts:
        return {"text": "", "confidence": 0.0}

    raw_text = "\n".join(texts)
    # TASK 4: ignore noise-level scores
    valid = [s for s in scores if s > 0.3]
    avg   = sum(valid) / len(valid) if valid else 0.0

    return {"text": raw_text, "confidence": float(avg)}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_text(file_path: str) -> dict:
    """
    Full pipeline: load → preprocess → OCR → merge.

    OUTPUT CONTRACT:
        {"raw_text": str, "confidence": float}
    Exactly 2 keys. Never raises.
    """
    _empty   = {"raw_text": "", "confidence": 0.0}
    filename = Path(file_path).name

    # STEP 6 — log file name
    logger.info("[INFO] File name: %s", filename)
    start = time.time()

    # ── Load ──────────────────────────────────────────────────────────────
    try:
        pages = load_pdf(file_path)
    except Exception as exc:
        logger.error("[ERROR] Load failed for %s: %s", filename, exc)
        return _empty

    if not pages:
        logger.error("[ERROR] 0 pages loaded for %s", filename)
        return _empty

    # STEP 6 — log page count
    logger.info("[INFO] Page count: %d", len(pages))

    # ── Per-page processing (parallelized) ────────────────────────────────
    def _process_page(args):
        page_idx, pil_image = args
        try:
            np_img = pil_to_numpy(pil_image)

            raw_result = run_ocr_on_image(np_img)

            if raw_result["confidence"] > 0.85:
                processed_result = {"text": "", "confidence": 0.0}
                logger.info("[INFO] Page %d: raw confidence %.4f > 0.85, skipping preprocessing",
                            page_idx, raw_result["confidence"])
            else:
                try:
                    preprocessed     = preprocess_image(np_img, apply_sharpen=False)
                    processed_result = run_ocr_on_image(preprocessed)
                except Exception as pp_exc:
                    logger.warning("[WARNING] Preprocessing failed p%d: %s", page_idx, pp_exc)
                    processed_result = {"text": "", "confidence": 0.0}

            if raw_result["confidence"] <= 0.85 and processed_result["confidence"] < _CONFIDENCE_SHARPEN_TH:
                try:
                    sharpened = preprocess_image(np_img, apply_sharpen=True)
                    retry     = run_ocr_on_image(sharpened)
                    if retry["confidence"] > processed_result["confidence"]:
                        processed_result = retry
                except Exception:
                    pass

            if processed_result["confidence"] > raw_result["confidence"]:
                ocr_result = processed_result
                logger.info("[INFO] Page %d: preprocessed wins (%.4f > %.4f)",
                            page_idx, processed_result["confidence"], raw_result["confidence"])
            else:
                ocr_result = raw_result
                logger.info("[INFO] Page %d: raw wins (%.4f >= %.4f)",
                            page_idx, raw_result["confidence"], processed_result["confidence"])

            text = ocr_result["text"]
            conf = ocr_result["confidence"]

            if not text.strip():
                logger.warning("[WARNING] Page %d blank — skipping", page_idx)
                return ("", None)

            logger.info("[INFO] Page %d confidence: %.4f", page_idx, conf)
            if conf < _CONFIDENCE_LOW_PAGE:
                logger.warning("[WARNING] Page %d confidence < 0.65: %.4f", page_idx, conf)
            return (text, conf)

        except Exception as exc:
            logger.error("[ERROR] Page %d of %s failed: %s", page_idx, filename, exc)
            return ("", None)

    page_texts       = []
    page_confidences = []

    indexed_pages = list(enumerate(pages, start=1))
    if len(indexed_pages) == 1:
        # Single page: avoid thread overhead
        text, conf = _process_page(indexed_pages[0])
        page_texts.append(text)
        if conf is not None:
            page_confidences.append(conf)
    else:
        max_workers = min(4, len(indexed_pages))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for text, conf in executor.map(_process_page, indexed_pages):
                page_texts.append(text)
                if conf is not None:
                    page_confidences.append(conf)

    # TASK 5 — multi-page integrity
    if len(pages) != len(page_texts):
        logger.error("[ERROR] Page mismatch: expected %d, got %d slots",
                     len(pages), len(page_texts))

    seen = set()
    for idx, txt in enumerate(page_texts, 1):
        c = txt.strip()
        if c:
            if c in seen:
                logger.warning("[WARNING] Duplicate page text on page %d", idx)
            seen.add(c)

    # ── Merge ──────────────────────────────────────────────────────────────
    non_empty = [t for t in page_texts if t.strip()]
    if not non_empty:
        logger.warning("[WARNING] No text extracted from %s", filename)
        return _empty

    raw_text = "\n".join(non_empty)

    # TASK 4 — confidence: skip blanks, filter < 0.3
    valid_confs = [c for c in page_confidences if c > 0.3]
    avg_conf    = sum(valid_confs) / len(valid_confs) if valid_confs else 0.0

    elapsed = time.time() - start
    logger.info("[INFO] Processing time: %.2fs", elapsed)
    logger.info("[INFO] Average confidence: %.4f", avg_conf)

    return {"raw_text": str(raw_text), "confidence": float(round(avg_conf, 4))}
