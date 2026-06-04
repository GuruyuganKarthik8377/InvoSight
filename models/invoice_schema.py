from typing import Optional, List

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    amount: Optional[float] = None


class InvoiceSchema(BaseModel):
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    currency: Optional[str] = None

    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None

    line_items: List[LineItem] = Field(default_factory=list)

    confidence: float
    extraction_status: str
    errors: List[str] = Field(default_factory=list)


def build_invoice_schema(
    cleaned_data: dict,
    errors: list,
    status: str,
    confidence: float,
) -> InvoiceSchema:
    if not isinstance(cleaned_data, dict):
        cleaned_data = {}

    raw_items = cleaned_data.get("line_items") or []
    if not isinstance(raw_items, list):
        raw_items = []

    items: List[LineItem] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        items.append(
            LineItem(
                description=item.get("description"),
                quantity=item.get("quantity"),
                unit_price=item.get("unit_price"),
                amount=item.get("amount"),
            )
        )

    return InvoiceSchema(
        vendor_name=cleaned_data.get("vendor_name"),
        invoice_number=cleaned_data.get("invoice_number"),
        invoice_date=cleaned_data.get("invoice_date"),
        currency=cleaned_data.get("currency"),
        subtotal=cleaned_data.get("subtotal"),
        tax=cleaned_data.get("tax"),
        total=cleaned_data.get("total"),
        line_items=items,
        confidence=confidence,
        extraction_status=status,
        errors=errors or [],
    )
