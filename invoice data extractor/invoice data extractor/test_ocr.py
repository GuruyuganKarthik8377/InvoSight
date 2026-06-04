import os
from services.ocr.ocr_service import extract_text

DATASET_DIR = "./datasets/invoices"


def validate_dataset():
    files = os.listdir("datasets/invoices")
    if len(files) < 10:
        raise ValueError("Dataset must contain at least 10 invoices")

    real_count = sum(1 for f in files if "real" in f.lower())
    if real_count < 5:
        raise ValueError("At least 5 real invoices required (filename must include 'real')")


def test_all():
    # Enforce real dataset requirement first
    validate_dataset()

    if not os.path.isdir(DATASET_DIR):
        print(f"Dataset directory not found: {DATASET_DIR}")
        return

    files = [f for f in os.listdir(DATASET_DIR) if not f.startswith(".")]
    if not files:
        print("No files found in dataset directory.")
        return

    passed = 0
    failed = 0

    for filename in sorted(files):
        path = os.path.join(DATASET_DIR, filename)
        if not os.path.isfile(path):
            continue

        print(f"\n--- Testing: {filename} ---")
        result = extract_text(path)
        print(f"Confidence : {result['confidence']:.2f}")
        print(f"Text length: {len(result['raw_text'])} chars")
        print(f"Preview    : {result['raw_text'][:300]}")

        if result["raw_text"] and result["confidence"] > 0.0:
            print("STATUS: PASS")
            passed += 1
        else:
            print("STATUS: FAIL")
            failed += 1

    print(f"\n=== Results: {passed} passed, {failed} failed ===")


if __name__ == "__main__":
    test_all()
