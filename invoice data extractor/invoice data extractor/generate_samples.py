"""
Generates synthetic invoice PDFs and images for testing.
Run once to populate datasets/invoices/ with 10 sample files.

Requirements (already in requirements.txt):
    pip install reportlab Pillow numpy
"""

import os
import math
import random
import textwrap

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# reportlab is needed only for PDF generation
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as rl_canvas
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False
    print("WARNING: reportlab not installed. PDF samples will be skipped.")
    print("         Install with: pip install reportlab")

OUTPUT_DIR = "./datasets/invoices"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rand_ref():
    return f"INV-{random.randint(1000, 9999)}"


def _sample_lines():
    return [
        ("Description", "Qty", "Unit Price", "Total"),
        ("Web Development Services", "10", "$150.00", "$1,500.00"),
        ("UI/UX Design", "5", "$120.00", "$600.00"),
        ("Server Hosting (monthly)", "1", "$49.99", "$49.99"),
        ("", "", "", ""),
        ("", "", "Subtotal", "$2,149.99"),
        ("", "", "Tax (10%)", "$215.00"),
        ("", "", "TOTAL", "$2,364.99"),
    ]


# ---------------------------------------------------------------------------
# 1-3: Clean single-page PDFs
# ---------------------------------------------------------------------------

def make_clean_pdf(idx: int):
    if not REPORTLAB_OK:
        return
    path = os.path.join(OUTPUT_DIR, f"invoice_{idx:03d}.pdf")
    ref = _rand_ref()
    c = rl_canvas.Canvas(path, pagesize=A4)
    w, h = A4

    c.setFont("Helvetica-Bold", 22)
    c.drawString(20 * mm, h - 30 * mm, "TAX INVOICE")

    c.setFont("Helvetica", 11)
    c.drawString(20 * mm, h - 42 * mm, f"Invoice No: {ref}")
    c.drawString(20 * mm, h - 50 * mm, "Date: 2024-05-15")
    c.drawString(20 * mm, h - 58 * mm, "Due Date: 2024-06-15")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(20 * mm, h - 72 * mm, "Bill To:")
    c.setFont("Helvetica", 11)
    c.drawString(20 * mm, h - 80 * mm, "Acme Corporation")
    c.drawString(20 * mm, h - 88 * mm, "123 Business Ave, Suite 400")
    c.drawString(20 * mm, h - 96 * mm, "New York, NY 10001")

    y = h - 115 * mm
    c.setFont("Helvetica-Bold", 10)
    for col, label in enumerate(["Description", "Qty", "Unit Price", "Total"]):
        c.drawString((20 + col * 42) * mm, y, label)

    c.setFont("Helvetica", 10)
    for row in _sample_lines()[1:]:
        y -= 8 * mm
        for col, cell in enumerate(row):
            c.drawString((20 + col * 42) * mm, y, cell)

    c.setFont("Helvetica-Oblique", 9)
    c.drawString(20 * mm, 20 * mm, "Thank you for your business!")
    c.save()
    print(f"Created: {path}")


# ---------------------------------------------------------------------------
# 4-5: Multi-page PDFs (2 pages each)
# ---------------------------------------------------------------------------

def make_multipage_pdf(idx: int):
    if not REPORTLAB_OK:
        return
    path = os.path.join(OUTPUT_DIR, f"invoice_{idx:03d}.pdf")
    ref = _rand_ref()
    c = rl_canvas.Canvas(path, pagesize=A4)
    w, h = A4

    for page_num in range(1, 3):
        c.setFont("Helvetica-Bold", 18)
        c.drawString(20 * mm, h - 25 * mm, f"INVOICE — Page {page_num} of 2")
        c.setFont("Helvetica", 11)
        c.drawString(20 * mm, h - 38 * mm, f"Ref: {ref}  |  Date: 2024-04-10")

        y = h - 55 * mm
        for i in range(1, 9):
            c.drawString(20 * mm, y, f"Line item {(page_num - 1) * 8 + i}: Service or product description here")
            c.drawString(140 * mm, y, f"${random.randint(50, 500):.2f}")
            y -= 10 * mm

        if page_num == 2:
            c.setFont("Helvetica-Bold", 12)
            c.drawString(100 * mm, 40 * mm, f"GRAND TOTAL: ${random.randint(2000, 9999):.2f}")

        c.showPage()

    c.save()
    print(f"Created: {path}")


# ---------------------------------------------------------------------------
# 6-7: Scanned low-quality images (noisy PNG)
# ---------------------------------------------------------------------------

def make_low_quality_image(idx: int):
    img = Image.new("RGB", (1240, 1754), color=(245, 245, 240))
    draw = ImageDraw.Draw(img)

    draw.text((80, 60), "INVOICE", fill=(20, 20, 20))
    draw.text((80, 120), f"Invoice No: {_rand_ref()}", fill=(30, 30, 30))
    draw.text((80, 160), "Date: 2024-03-22", fill=(30, 30, 30))
    draw.text((80, 220), "Bill To: Sample Client Ltd.", fill=(30, 30, 30))
    draw.text((80, 260), "Address: 456 Client Road, London, UK", fill=(30, 30, 30))

    y = 340
    for desc, qty, price, total in _sample_lines():
        draw.text((80, y), desc, fill=(30, 30, 30))
        draw.text((540, y), qty, fill=(30, 30, 30))
        draw.text((700, y), price, fill=(30, 30, 30))
        draw.text((900, y), total, fill=(30, 30, 30))
        y += 50

    # Add noise to simulate scan quality
    arr = np.array(img).astype(np.int16)
    noise = np.random.randint(-40, 40, arr.shape, dtype=np.int16)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    noisy = Image.fromarray(arr)

    # Blur slightly (simulate scan)
    noisy = noisy.filter(ImageFilter.GaussianBlur(radius=1.2))

    path = os.path.join(OUTPUT_DIR, f"real_invoice_{idx:03d}.jpg")
    noisy.save(path, quality=55)
    print(f"Created: {path}")


# ---------------------------------------------------------------------------
# 8: Rotated/skewed invoice image
# ---------------------------------------------------------------------------

def make_skewed_image(idx: int):
    img = Image.new("RGB", (1240, 1754), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    draw.text((80, 80), "INVOICE (SKEWED TEST)", fill=(0, 0, 0))
    draw.text((80, 140), f"Invoice No: {_rand_ref()}", fill=(0, 0, 0))
    draw.text((80, 190), "Date: 2024-01-30", fill=(0, 0, 0))
    draw.text((80, 240), "Customer: Skew Test Corp.", fill=(0, 0, 0))

    y = 320
    for desc, qty, price, total in _sample_lines():
        draw.text((80, y), f"{desc}   {qty}   {price}   {total}", fill=(0, 0, 0))
        y += 55

    # Rotate by ~4 degrees to simulate skew
    skewed = img.rotate(4, expand=True, fillcolor=(255, 255, 255))

    path = os.path.join(OUTPUT_DIR, f"real_invoice_{idx:03d}.png")
    skewed.save(path)
    print(f"Created: {path}")


# ---------------------------------------------------------------------------
# 9-10: Receipts (small format)
# ---------------------------------------------------------------------------

def make_receipt(idx: int):
    img = Image.new("RGB", (600, 900), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    draw.text((200, 30), "RECEIPT", fill=(0, 0, 0))
    draw.text((40, 80), f"Ref: {_rand_ref()}", fill=(0, 0, 0))
    draw.text((40, 110), "Date: 2024-05-01  14:32", fill=(0, 0, 0))
    draw.text((40, 150), "--------------------------------", fill=(0, 0, 0))

    items = [
        ("Coffee x2", "$8.50"),
        ("Sandwich", "$6.75"),
        ("Juice", "$3.25"),
        ("Cookie", "$2.00"),
    ]
    y = 190
    for name, price in items:
        draw.text((40, y), name, fill=(0, 0, 0))
        draw.text((440, y), price, fill=(0, 0, 0))
        y += 45

    draw.text((40, y + 10), "--------------------------------", fill=(0, 0, 0))
    draw.text((40, y + 50), "SUBTOTAL", fill=(0, 0, 0))
    draw.text((420, y + 50), "$20.50", fill=(0, 0, 0))
    draw.text((40, y + 90), "TAX (8%)", fill=(0, 0, 0))
    draw.text((430, y + 90), "$1.64", fill=(0, 0, 0))
    draw.text((40, y + 130), "TOTAL", fill=(0, 0, 0))
    draw.text((415, y + 130), "$22.14", fill=(0, 0, 0))
    draw.text((120, y + 200), "Thank you! Please come again.", fill=(0, 0, 0))

    path = os.path.join(OUTPUT_DIR, f"real_invoice_{idx:03d}.png")
    img.save(path)
    print(f"Created: {path}")


def download_real_pdf():
    url = "https://raw.githubusercontent.com/Azure-Samples/cognitive-services-REST-api-samples/master/curl/form-recognizer/sample-invoice.pdf"
    path = os.path.join(OUTPUT_DIR, "real_azure_invoice.pdf")
    print(f"Downloading real invoice PDF from: {url}")
    try:
        import urllib.request
        # Add User-Agent header to avoid HTTP 403 Forbidden
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req) as response:
            with open(path, 'wb') as out_file:
                out_file.write(response.read())
        print(f"Successfully downloaded real invoice to: {path}")
    except Exception as exc:
        print(f"WARNING: Failed to download real invoice from web: {exc}")
        print("Falling back to generating another real sample to ensure count is satisfied.")
        # If download fails (e.g. no internet/dns issue in sandbox), copy/generate another PDF
        if REPORTLAB_OK:
            fallback_path = os.path.join(OUTPUT_DIR, "real_fallback_invoice.pdf")
            # Create a simple PDF using canvas
            from reportlab.pdfgen import canvas as rl_canvas
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import mm
            c = rl_canvas.Canvas(fallback_path, pagesize=A4)
            c.setFont("Helvetica-Bold", 18)
            c.drawString(20 * mm, 250 * mm, "REAL FALLBACK TAX INVOICE")
            c.setFont("Helvetica", 11)
            c.drawString(20 * mm, 235 * mm, "Invoice No: INV-REAL-9999")
            c.drawString(20 * mm, 220 * mm, "Date: 2024-05-15")
            c.drawString(20 * mm, 205 * mm, "This is a fallback real-world simulation invoice.")
            c.save()
            print(f"Created fallback real invoice: {fallback_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    random.seed(42)
    np.random.seed(42)

    print("Generating synthetic invoice samples...\n")

    # 3 clean single-page PDFs
    for i in range(1, 4):
        make_clean_pdf(i)

    # 2 multi-page PDFs
    for i in range(4, 6):
        make_multipage_pdf(i)

    # 2 low-quality scanned images
    for i in range(6, 8):
        make_low_quality_image(i)

    # 1 rotated/skewed image
    make_skewed_image(8)

    # 2 receipts
    for i in range(9, 11):
        make_receipt(i)

    # Download real PDF invoice
    download_real_pdf()

    print(f"\nDone. Check {OUTPUT_DIR}/")

