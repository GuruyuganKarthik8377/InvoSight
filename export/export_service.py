import os
import json
import copy
from datetime import datetime

import pandas as pd


os.makedirs("outputs/json", exist_ok=True)
os.makedirs("outputs/excel", exist_ok=True)


LINE_ITEM_COLUMNS = ["description", "quantity", "unit_price", "amount"]


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def export_json(data: dict) -> str:
    os.makedirs("outputs/json", exist_ok=True)
    filename = f"outputs/json/invoice_{_timestamp()}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    return filename


def export_excel(data: dict) -> str:
    os.makedirs("outputs/excel", exist_ok=True)
    filename = f"outputs/excel/invoice_{_timestamp()}.xlsx"

    invoice_data = copy.deepcopy(data)
    line_items = invoice_data.pop("line_items", []) or []

    invoice_df = pd.DataFrame([invoice_data])

    if line_items:
        line_items_df = pd.DataFrame(line_items)
    else:
        line_items_df = pd.DataFrame(columns=LINE_ITEM_COLUMNS)

    with pd.ExcelWriter(filename, engine="openpyxl") as writer:
        invoice_df.to_excel(writer, sheet_name="Invoice", index=False)
        line_items_df.to_excel(writer, sheet_name="Line Items", index=False)

    return filename
