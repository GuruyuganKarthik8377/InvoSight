import os
import sys
from services.ocr.ocr_service import extract_text


def validate_output(file_path):
    result = extract_text(file_path)

    assert isinstance(result, dict)
    assert "raw_text" in result
    assert "confidence" in result
    assert isinstance(result["raw_text"], str)
    assert isinstance(result["confidence"], float)
    assert len(result.keys()) == 2

    if result["raw_text"]:
        assert len(result["raw_text"]) > 50

    return True


if __name__ == "__main__":
    dataset_dir = "datasets/invoices"
    if not os.path.exists(dataset_dir):
        print(f"Dataset directory {dataset_dir} does not exist!")
        sys.exit(1)

    files = [f for f in os.listdir(dataset_dir) if not f.startswith(".")]
    if not files:
        print("No files found to validate.")
        sys.exit(1)

    print(f"Validating {len(files)} files...")
    all_passed = True
    for filename in sorted(files):
        path = os.path.join(dataset_dir, filename)
        if not os.path.isfile(path):
            continue
        print(f"\n--- Validating: {filename} ---")
        try:
            passed = validate_output(path)
            if passed:
                print(f"PASS: {filename}")
            else:
                print(f"FAIL: {filename}")
                all_passed = False
        except Exception as exc:
            print(f"FAIL: {filename} due to exception: {exc}")
            all_passed = False

    if all_passed:
        print("\nAll files passed validation successfully!")
        sys.exit(0)
    else:
        print("\nSome files failed validation.")
        sys.exit(1)
