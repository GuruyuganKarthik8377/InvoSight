"""
PDF Loader — uses pypdfium2 exclusively (no Poppler / pdftoppm required).
For image files (.png, .jpg, .jpeg) PIL is used directly.
"""
import logging
import shutil
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)

_SUPPORTED_IMAGES = {".png", ".jpg", ".jpeg"}
_SUPPORTED_ALL    = {".pdf", ".png", ".jpg", ".jpeg"}

try:
    import os
    _DPI = int(os.getenv("OCR_DPI", "200"))
except Exception:
    _DPI = 300


def check_poppler() -> bool:
    """Diagnostic helper — returns True if Poppler is present, False otherwise."""
    found = shutil.which("pdftoppm") is not None
    if not found:
        logger.warning("[WARNING] Poppler (pdftoppm) not in PATH — using pypdfium2 instead")
    return found


def load_pdf(file_path: str, dpi: int = _DPI) -> list:
    """
    Load a PDF or image file and return a list of PIL RGB Images (one per page).

    PDF engine : pypdfium2  (no system dependencies)
    Image types: .png / .jpg / .jpeg — loaded directly via Pillow

    Returns [] on any unrecoverable error (never raises).
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix not in _SUPPORTED_ALL:
        raise ValueError(f"Unsupported file type: {suffix}")

    if not path.exists():
        raise RuntimeError(f"File not found: {file_path}")

    # ── Image files ──────────────────────────────────────────────────────────
    if suffix in _SUPPORTED_IMAGES:
        try:
            img = Image.open(str(path)).convert("RGB")
            img.load()
            logger.info("[INFO] Loaded image: %s", path.name)
            return [img]
        except Exception as exc:
            logger.error("[ERROR] Failed to open image %s: %s", path.name, exc)
            return []

    # ── PDF files — pypdfium2 ─────────────────────────────────────────────
    try:
        import pypdfium2 as pdfium
    except ImportError:
        logger.error(
            "[ERROR] pypdfium2 is not installed. "
            "Install with: pip install pypdfium2"
        )
        return []

    try:
        pdf    = pdfium.PdfDocument(str(path))
        scale  = dpi / 72.0          # pypdfium2 native resolution is 72 DPI
        pages  = []
        for page_idx, page in enumerate(pdf, start=1):
            try:
                bitmap    = page.render(scale=scale, rotation=0)
                pil_image = bitmap.to_pil().convert("RGB")
                pages.append(pil_image)
            except Exception as exc:
                logger.error(
                    "[ERROR] Failed to render PDF page %d of %s: %s",
                    page_idx, path.name, exc
                )
        if pages:
            logger.info("[INFO] PDF '%s' loaded via pypdfium2 (%d pages)", path.name, len(pages))
        else:
            logger.error("[ERROR] pypdfium2 produced 0 pages for %s", path.name)
        return pages
    except Exception as exc:
        logger.error("[ERROR] pypdfium2 failed to open PDF %s: %s", path.name, exc)
        return []
