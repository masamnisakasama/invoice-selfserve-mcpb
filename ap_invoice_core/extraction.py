from __future__ import annotations

import json
from datetime import date
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
        source="claude_desktop_vision_ocr",
    )


def _fv(document_type: str, document_name: str, field: str, value: Any) -> FieldValue:
    return FieldValue(value=value, confidence=0.99, evidence=[_ev(document_type, document_name, field, value)])


def _load_sidecar(pdf_path: Path, expected_document_type: str) -> dict[str, Any]:
    sidecar = pdf_path.with_suffix(".json")
    if not sidecar.is_file():
        raise FileNotFoundError(f"Missing extraction sidecar: {sidecar}")
    data = json.loads(sidecar.read_text("utf-8"))
    actual_document_type = data.get("document_type")
    if actual_document_type != expected_document_type:
        raise ValueError(
            f"Sidecar document_type mismatch for {pdf_path.name}: "
            f"expected {expected_document_type}, got {actual_document_type}"
        )
    return data


def load_canonical_from_documents(
    *,
    invoice_pdf: str | Path,
    purchase_order_pdf: str | Path,
    goods_receipt_pdf: str | Path,
) -> CanonicalFacts:
    raise RuntimeError(
        "Legacy sidecar extraction is disabled in the Claude OCR MCPB. "
        "Use canonical_from_ocr_results after ap_invoice_submit_ocr_result."
    )


def canonical_from_ocr_results(
    *,
    invoice_ocr: dict[str, Any],
    purchase_order_ocr: dict[str, Any],
    goods_receipt_ocr: dict[str, Any],
) -> CanonicalFacts:
    return CanonicalFacts(
        invoice=_invoice(_normalize_ocr_document(invoice_ocr, "invoice"), _document_name(invoice_ocr, "invoice.pdf")),
        purchase_order=_po(
            _normalize_ocr_document(purchase_order_ocr, "purchase_order"),
            _document_name(purchase_order_ocr, "purchase_order.pdf"),
        ),
        goods_receipt=_grn(
            _normalize_ocr_document(goods_receipt_ocr, "goods_receipt"),
            _document_name(goods_receipt_ocr, "goods_receipt.pdf"),
        ),
    )


def _normalize_ocr_document(data: dict[str, Any], expected_document_type: str) -> dict[str, Any]:
    actual_document_type = data.get("document_type")
    if actual_document_type != expected_document_type:
        raise ValueError(
            f"OCR document_type mismatch: expected {expected_document_type}, got {actual_document_type}"
        )
    fields = dict(data.get("fields") or {})
    for field in (
        "subtotal_amount",
        "tax_amount",
        "total_amount",
        "remaining_balance",
        "received_quantity",
    ):
        if field in fields:
            fields[field] = _normalize_int(fields[field])
    if "approved" in fields:
        fields["approved"] = _normalize_bool(fields["approved"])
    if "received" in fields:
        fields["received"] = _normalize_bool(fields["received"])
    for item in fields.get("line_items") or []:
        if not isinstance(item, dict):
            continue
        for field in ("quantity", "unit_price", "amount"):
            if field in item:
                item[field] = _normalize_number(item[field])
        item.setdefault("tax_code", fields.get("tax_code", "JP10"))
    return {"document_type": expected_document_type, "fields": fields}


def _document_name(data: dict[str, Any], default: str) -> str:
    value = data.get("document_name")
    return str(value).strip() if value else default


def _normalize_int(value: Any) -> int:
    return int(_normalize_number(value))


def _normalize_number(value: Any) -> float:
    if isinstance(value, bool) or value is None:
        raise ValueError(f"Expected numeric OCR value, got {value!r}")
    if isinstance(value, int | float):
        return value
    text = str(value)
    digits = "".join(ch for ch in text if ch.isdigit() or ch in ".-")
    if digits in {"", "-", ".", "-."}:
        raise ValueError(f"Expected numeric OCR value, got {value!r}")
    number = float(digits)
    return int(number) if number.is_integer() else number


def _normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "yes", "y", "1", "received", "approved"}:
        return True
    if text in {"false", "no", "n", "0", "not received", "not approved"}:
        return False
    raise ValueError(f"Expected boolean OCR value, got {value!r}")


def _line_items(items: list[dict[str, Any]]) -> list[InvoiceLineItem]:
    line_items = [InvoiceLineItem(**item) for item in items]
    for item in line_items:
        _require_positive_number("line_items.quantity", item.quantity)
        _require_non_negative_number("line_items.unit_price", item.unit_price)
        _require_non_negative_number("line_items.amount", item.amount)
    return line_items


def _invoice(data: dict[str, Any], document_name: str) -> InvoiceFacts:
    fields = data["fields"]
    _validate_iso_date("invoice_date", fields["invoice_date"])
    if fields.get("due_date"):
        _validate_iso_date("due_date", fields["due_date"])
    for field in ("subtotal_amount", "tax_amount", "total_amount"):
        _require_non_negative_number(field, fields[field])
    _require_non_empty("invoice_number", fields["invoice_number"])
    _require_non_empty("vendor_id", fields["vendor_id"])
    _require_non_empty("po_number", fields["po_number"])
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
    _require_non_empty("po_number", fields["po_number"])
    _require_non_empty("vendor_id", fields["vendor_id"])
    _require_non_negative_number("total_amount", fields["total_amount"])
    _require_non_negative_number("remaining_balance", fields["remaining_balance"])
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
    _require_non_empty("receipt_number", fields["receipt_number"])
    _require_non_empty("po_number", fields["po_number"])
    _require_non_negative_number("received_quantity", fields["received_quantity"])
    _validate_iso_date("receipt_date", fields["receipt_date"])
    dt = "goods_receipt"
    return GoodsReceiptFacts(
        receipt_number=_fv(dt, document_name, "receipt_number", fields["receipt_number"]),
        po_number=_fv(dt, document_name, "po_number", fields["po_number"]),
        received=_fv(dt, document_name, "received", fields["received"]),
        received_quantity=_fv(dt, document_name, "received_quantity", fields["received_quantity"]),
        receipt_date=_fv(dt, document_name, "receipt_date", fields["receipt_date"]),
    )


def _require_non_empty(field: str, value: Any) -> None:
    if value is None or str(value).strip() == "":
        raise ValueError(f"{field} is required")


def _require_non_negative_number(field: str, value: Any) -> None:
    number = float(value)
    if number < 0:
        raise ValueError(f"{field} must be non-negative")


def _require_positive_number(field: str, value: Any) -> None:
    number = float(value)
    if number <= 0:
        raise ValueError(f"{field} must be positive")


def _validate_iso_date(field: str, value: Any) -> None:
    parsed = date.fromisoformat(str(value))
    if parsed.year < 2000:
        raise ValueError(f"{field} is outside the supported demo date range")
