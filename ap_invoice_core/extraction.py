from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import (
    CanonicalFacts,
    Evidence,
    FieldValue,
    GoodsReceiptFacts,
    InvoiceFacts,
    InvoiceLineItem,
    PurchaseOrderFacts,
)


def _ev(document_type: str, document_name: str, field: str, value: Any) -> Evidence:
    return Evidence(
        document_type=document_type,
        document_name=document_name,
        page=1,
        field_label=field,
        raw_text=str(value),
        normalized_value=value,
    )


def _fv(document_type: str, document_name: str, field: str, value: Any) -> FieldValue:
    return FieldValue(value=value, confidence=0.99, evidence=[_ev(document_type, document_name, field, value)])


def _load_sidecar(pdf_path: Path) -> dict[str, Any]:
    sidecar = pdf_path.with_suffix(".json")
    if not sidecar.is_file():
        raise FileNotFoundError(f"Missing extraction sidecar: {sidecar}")
    return json.loads(sidecar.read_text("utf-8"))


def load_canonical_from_documents(
    *,
    invoice_pdf: str | Path,
    purchase_order_pdf: str | Path,
    goods_receipt_pdf: str | Path,
) -> CanonicalFacts:
    invoice_data = _load_sidecar(Path(invoice_pdf))
    po_data = _load_sidecar(Path(purchase_order_pdf))
    grn_data = _load_sidecar(Path(goods_receipt_pdf))
    return CanonicalFacts(
        invoice=_invoice(invoice_data, Path(invoice_pdf).name),
        purchase_order=_po(po_data, Path(purchase_order_pdf).name),
        goods_receipt=_grn(grn_data, Path(goods_receipt_pdf).name),
    )


def _line_items(items: list[dict[str, Any]]) -> list[InvoiceLineItem]:
    return [InvoiceLineItem(**item) for item in items]


def _invoice(data: dict[str, Any], document_name: str) -> InvoiceFacts:
    fields = data["fields"]
    dt = "invoice"
    return InvoiceFacts(
        invoice_number=_fv(dt, document_name, "invoice_number", fields["invoice_number"]),
        invoice_date=_fv(dt, document_name, "invoice_date", fields["invoice_date"]),
        due_date=_fv(dt, document_name, "due_date", fields.get("due_date")),
        vendor_name=_fv(dt, document_name, "vendor_name", fields["vendor_name"]),
        vendor_id=_fv(dt, document_name, "vendor_id", fields["vendor_id"]),
        po_number=_fv(dt, document_name, "po_number", fields["po_number"]),
        currency=_fv(dt, document_name, "currency", fields["currency"]),
        subtotal_amount=_fv(dt, document_name, "subtotal_amount", fields["subtotal_amount"]),
        tax_amount=_fv(dt, document_name, "tax_amount", fields["tax_amount"]),
        total_amount=_fv(dt, document_name, "total_amount", fields["total_amount"]),
        bank_account=_fv(dt, document_name, "bank_account", fields["bank_account"]),
        tax_code=_fv(dt, document_name, "tax_code", fields["tax_code"]),
        cost_center=_fv(dt, document_name, "cost_center", fields.get("cost_center")),
        line_items=_line_items(fields["line_items"]),
    )


def _po(data: dict[str, Any], document_name: str) -> PurchaseOrderFacts:
    fields = data["fields"]
    dt = "purchase_order"
    return PurchaseOrderFacts(
        po_number=_fv(dt, document_name, "po_number", fields["po_number"]),
        vendor_id=_fv(dt, document_name, "vendor_id", fields["vendor_id"]),
        currency=_fv(dt, document_name, "currency", fields["currency"]),
        total_amount=_fv(dt, document_name, "total_amount", fields["total_amount"]),
        approved=_fv(dt, document_name, "approved", fields["approved"]),
        remaining_balance=_fv(dt, document_name, "remaining_balance", fields["remaining_balance"]),
        line_items=_line_items(fields["line_items"]),
    )


def _grn(data: dict[str, Any], document_name: str) -> GoodsReceiptFacts:
    fields = data["fields"]
    dt = "goods_receipt"
    return GoodsReceiptFacts(
        receipt_number=_fv(dt, document_name, "receipt_number", fields["receipt_number"]),
        po_number=_fv(dt, document_name, "po_number", fields["po_number"]),
        received=_fv(dt, document_name, "received", fields["received"]),
        received_quantity=_fv(dt, document_name, "received_quantity", fields["received_quantity"]),
        receipt_date=_fv(dt, document_name, "receipt_date", fields["receipt_date"]),
    )

