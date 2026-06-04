import os
import logging
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

_SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}


def is_supported_file(file_path: str) -> bool:
    """Returns True if extension is pdf, png, jpg, jpeg."""
    return Path(file_path).suffix.lower() in _SUPPORTED_EXTENSIONS


def pil_to_numpy(image: Image.Image) -> np.ndarray:
    """Converts PIL Image to NumPy array (RGB -> BGR for OpenCV)."""
    rgb = np.array(image.convert("RGB"))
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    return bgr


def numpy_to_pil(image: np.ndarray) -> Image.Image:
    """Converts NumPy array back to PIL Image."""
    if len(image.shape) == 2:
        return Image.fromarray(image)
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb)


def save_debug_image(image: np.ndarray, filename: str) -> None:
    """Saves preprocessed image to logs/ for debugging."""
    log_dir = os.getenv("LOG_DIR", "./logs")
    os.makedirs(log_dir, exist_ok=True)
    dest = os.path.join(log_dir, filename)
    try:
        cv2.imwrite(dest, image)
        logger.debug("Debug image saved: %s", dest)
    except Exception as exc:
        logger.warning("Could not save debug image %s: %s", dest, exc)
