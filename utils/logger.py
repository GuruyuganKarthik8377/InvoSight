import logging
import os


os.makedirs("logs", exist_ok=True)

logger = logging.getLogger("invoice_extractor")
logger.setLevel(logging.INFO)

if not logger.handlers:
    file_handler = logging.FileHandler("logs/extraction.log", encoding="utf-8")
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

logger.propagate = False
