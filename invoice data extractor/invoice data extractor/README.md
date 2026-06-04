# OCR + Document Ingestion Pipeline

OCR pipeline for invoice extraction. Feeds Person B's LLM extraction layer.

## Output Contract

Every `extract_text()` call returns:
```json
{
  "raw_text": "full extracted text across all pages",
  "confidence": 0.91
}
```

## Setup

### 1. Install system dependency (Poppler — required by pdf2image)

**Windows:**
Download from https://github.com/oschwartz10612/poppler-windows/releases/
and add the `bin/` folder to your system PATH.

**Linux/macOS:**
```bash
sudo apt install poppler-utils   # Ubuntu/Debian
brew install poppler             # macOS
```

### 2. Create virtual environment & install packages

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux/macOS

pip install -r requirements.txt
pip install reportlab           # only needed to generate synthetic samples
```

### 3. Generate test samples (10 synthetic invoices)

```bash
python generate_samples.py
```

Or manually place real invoice PDFs/images into `datasets/invoices/`
named `invoice_001.pdf`, `invoice_002.pdf`, etc.

### 4. Run tests

```bash
python test_ocr.py
```

## File Structure

```
backend/
  services/
    ocr/
      ocr_service.py      ← core pipeline + extract_text()
      preprocessing.py    ← image preprocessing (grayscale, blur, Otsu, deskew)
      pdf_loader.py       ← PDF/image → list of PIL Images
      utils.py            ← helpers: pil_to_numpy, save_debug_image, etc.
  datasets/
    invoices/             ← sample PDFs/images
    receipts/             ← sample receipts
  logs/
    ocr.log               ← auto-created on first run
  test_ocr.py
  generate_samples.py
  .env
  requirements.txt
```

## Environment Variables (`.env`)

| Variable | Default | Description |
|---|---|---|
| `OCR_DPI` | 300 | DPI for PDF rasterisation |
| `OCR_LANG` | en | PaddleOCR language |
| `LOG_DIR` | ./logs | Log directory |
| `DATASET_DIR` | ./datasets/invoices | Dataset directory |
| `DEBUG_IMAGES` | false | Save preprocessed images to logs/ |

## Logging

Logs are written to `logs/ocr.log`. Key events:
- `INFO` — file name, page count, elapsed time, average confidence
- `WARNING` — page confidence < 0.65
- `ERROR` — file load failures or OCR exceptions

## Performance Targets

| Metric | Target |
|---|---|
| Time per page | < 5 seconds |
| Clean invoice confidence | > 0.80 |
| Low-quality scan confidence | > 0.60 |
| Crash rate | 0% |
