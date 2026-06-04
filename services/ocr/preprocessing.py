import logging

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

_SKEW_THRESHOLD = 0.5  # degrees


def deskew(image: np.ndarray) -> np.ndarray:
    """
    Detects skew angle using Hough transform.
    Rotates image to correct skew.
    Only apply if angle > 0.5 degrees.
    """
    coords = np.column_stack(np.where(image > 0))
    if coords.size == 0:
        return image

    angle = cv2.minAreaRect(coords)[-1]

    if angle < -45:
        angle = 90 + angle

    if abs(angle) < _SKEW_THRESHOLD:
        return image

    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        image,
        rotation_matrix,
        (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return rotated


def _sharpen(image: np.ndarray) -> np.ndarray:
    """Applies an unsharp mask sharpen filter."""
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
    return cv2.filter2D(image, -1, kernel)


def preprocess_image(image, apply_sharpen: bool = False) -> np.ndarray:
    """
    Accepts PIL Image or np.ndarray.
    Returns: preprocessed np.ndarray (grayscale, thresholded)

    Pipeline (in order):
    1. Convert to grayscale
    2. Gaussian blur (3x3)
    3. Otsu thresholding
    4. Deskew (if tilt > 0.5 degrees)
    5. Sharpen (optional, only if apply_sharpen=True)
    """
    if isinstance(image, Image.Image):
        arr = np.array(image.convert("RGB"))
        bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    elif isinstance(image, np.ndarray):
        bgr = image
    else:
        raise TypeError("Expected PIL Image or np.ndarray")

    # Step 1 — Grayscale
    if len(bgr.shape) == 3:
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    else:
        gray = bgr

    # Step 2 — Gaussian blur
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)

    # Step 3 — Otsu thresholding
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Step 4 — Deskew
    try:
        deskewed = deskew(thresh)
    except Exception as exc:
        logger.warning("Deskew failed, skipping: %s", exc)
        deskewed = thresh

    # Step 5 — Optional sharpen
    if apply_sharpen:
        try:
            deskewed = _sharpen(deskewed)
        except Exception as exc:
            logger.warning("Sharpen failed, skipping: %s", exc)

    return deskewed
