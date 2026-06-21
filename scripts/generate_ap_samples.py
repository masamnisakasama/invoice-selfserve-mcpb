from __future__ import annotations

import json
import shutil
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROOT_SAMPLES = PROJECT_ROOT / "samples"
PACK_SAMPLES = PROJECT_ROOT / "workflow-packs" / "ap-invoice-v1" / "samples"
PACK_TESTS = PROJECT_ROOT / "workflow-packs" / "ap-invoice-v1" / "tests"


def line_item(amount: int = 100000, quantity: int = 100) -> dict[str, Any]:
    return {
        "description": "Office supplies bundle",
        "quantity": quantity,
        "unit_price": amount / quantity,
        "amount": amount,
        "tax_code": "JP10",
    }


def invoice_fields(
    *,
    invoice_number: str,
    po_number: str,
    total_amount: int,
    bank_account: str = "0001-1234567",
    vendor_id: str = "V-1001",
    invoice_date: str = "2026-06-20",
    quantity: int = 100,
    subtotal_amount: int | None = None,
    tax_amount: int | None = None,
) -> dict[str, Any]:
    subtotal = subtotal_amount if subtotal_amount is not None else round(total_amount / 1.1)
    tax = tax_amount if tax_amount is not None else total_amount - subtotal
    due_date = (date.fromisoformat(invoice_date) + timedelta(days=30)).isoformat()
    return {
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
        "due_date": due_date,
        "vendor_name": "Tokyo Office Supply Co.",
        "vendor_id": vendor_id,
        "po_number": po_number,
        "currency": "JPY",
        "subtotal_amount": subtotal,
        "tax_amount": tax,
        "total_amount": total_amount,
        "bank_account": bank_account,
        "tax_code": "JP10",
        "cost_center": "CC-ADMIN",
        "line_items": [line_item(subtotal, quantity)],
    }


def po_fields(*, po_number: str, total_amount: int = 110000) -> dict[str, Any]:
    subtotal = round(total_amount / 1.1)
    return {
        "po_number": po_number,
        "vendor_id": "V-1001",
        "currency": "JPY",
        "total_amount": total_amount,
        "approved": True,
        "remaining_balance": total_amount,
        "line_items": [line_item(subtotal, 100)],
    }


def grn_fields(*, receipt_number: str, po_number: str, quantity: int = 100) -> dict[str, Any]:
    return {
        "receipt_number": receipt_number,
        "po_number": po_number,
        "received": True,
        "received_quantity": quantity,
        "receipt_date": "2026-06-18",
    }


def write_document_pdf(path: Path, *, document_type: str, fields: dict[str, Any]) -> None:
    image = Image.new("RGB", (1240, 1754), "white")
    draw = ImageDraw.Draw(image)
    title_font = _font(54)
    section_font = _font(34)
    body_font = _font(28)
    small_font = _font(22)

    title = {
        "invoice": "INVOICE",
        "purchase_order": "PURCHASE ORDER",
        "goods_receipt": "GOODS RECEIPT / INSPECTION REPORT",
    }[document_type]
    draw.rectangle((48, 48, 1192, 1706), outline="black", width=4)
    draw.text((90, 86), title, fill="black", font=title_font)
    draw.line((90, 165, 1150, 165), fill="black", width=3)

    y = 220
    for label, value in _display_rows(document_type, fields):
        if label == "Line Items":
            y += 18
            draw.text((90, y), "Line Items", fill="black", font=section_font)
            y += 54
            continue
        draw.text((110, y), f"{label}: {value}", fill="black", font=body_font)
        y += 46

    draw.text((90, 1640), "Fictional AP Invoice OCR demo data only", fill="black", font=small_font)
    buffer = BytesIO()
    image.save(buffer, format="PDF", resolution=150.0)
    path.write_bytes(buffer.getvalue())


def _display_rows(document_type: str, fields: dict[str, Any]) -> list[tuple[str, Any]]:
    if document_type == "invoice":
        item = fields["line_items"][0]
        return [
            ("Invoice No", fields["invoice_number"]),
            ("Invoice Date", fields["invoice_date"]),
            ("Due Date", fields["due_date"]),
            ("Vendor", fields["vendor_name"]),
            ("Vendor ID", fields["vendor_id"]),
            ("Bank Account", fields["bank_account"]),
            ("PO No", fields["po_number"]),
            ("Currency", fields["currency"]),
            ("Tax Code", fields["tax_code"]),
            ("Cost Center", fields["cost_center"]),
            ("Line Items", ""),
            ("Description", item["description"]),
            ("Quantity", _format_number(item["quantity"])),
            ("Unit Price", f"JPY {_format_number(item['unit_price'])}"),
            ("Amount", f"JPY {_format_number(item['amount'])}"),
            ("Subtotal", f"JPY {_format_number(fields['subtotal_amount'])}"),
            ("Tax", f"JPY {_format_number(fields['tax_amount'])}"),
            ("Total", f"JPY {_format_number(fields['total_amount'])}"),
        ]
    if document_type == "purchase_order":
        item = fields["line_items"][0]
        return [
            ("PO No", fields["po_number"]),
            ("Vendor ID", fields["vendor_id"]),
            ("Currency", fields["currency"]),
            ("Approved", "Yes" if fields["approved"] else "No"),
            ("Remaining Balance", f"JPY {_format_number(fields['remaining_balance'])}"),
            ("Line Items", ""),
            ("Description", item["description"]),
            ("Quantity", _format_number(item["quantity"])),
            ("Unit Price", f"JPY {_format_number(item['unit_price'])}"),
            ("Amount", f"JPY {_format_number(item['amount'])}"),
            ("Total", f"JPY {_format_number(fields['total_amount'])}"),
        ]
    return [
        ("Receipt No", fields["receipt_number"]),
        ("PO No", fields["po_number"]),
        ("Received", "Yes" if fields["received"] else "No"),
        ("Received Quantity", _format_number(fields["received_quantity"])),
        ("Receipt Date", fields["receipt_date"]),
        ("Item", "Office supplies bundle"),
    ]


def _format_number(value: Any) -> str:
    number = float(value)
    if number.is_integer():
        return f"{int(number):,}"
    return f"{number:,.2f}"


def _font(size: int) -> Any:
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size=size)
    except OSError:
        return ImageFont.load_default()


CASES: dict[str, dict[str, Any]] = {
    "case-a-pay-ready": {
        "invoice": invoice_fields(
            invoice_number="INV-2026-0008",
            po_number="PO-2026-0001",
            total_amount=110000,
            invoice_date="2026-07-15",
        ),
        "purchase_order": po_fields(po_number="PO-2026-0001", total_amount=110000),
        "goods_receipt": grn_fields(receipt_number="GRN-2026-0001", po_number="PO-2026-0001"),
        "expected": {"recommendation": "PAY_READY_CANDIDATE", "rule_ids": []},
    },
    "case-b-po-mismatch": {
        "invoice": invoice_fields(invoice_number="INV-2026-0009", po_number="PO-2026-0002", total_amount=121000),
        "purchase_order": po_fields(po_number="PO-2026-0002", total_amount=110000),
        "goods_receipt": grn_fields(receipt_number="GRN-2026-0002", po_number="PO-2026-0002"),
        "expected": {"recommendation": "REFER_PO_MISMATCH", "rule_ids": ["AP-PO-001"]},
    },
    "case-c-duplicate": {
        "invoice": invoice_fields(invoice_number="INV-2026-0007", po_number="PO-2026-0003", total_amount=110000),
        "purchase_order": po_fields(po_number="PO-2026-0003", total_amount=110000),
        "goods_receipt": grn_fields(receipt_number="GRN-2026-0003", po_number="PO-2026-0003"),
        "expected": {"recommendation": "REFER_DUPLICATE_REVIEW", "rule_ids": ["AP-DUP-001"]},
    },
    "case-d-vendor-review": {
        "invoice": invoice_fields(
            invoice_number="INV-2026-0010",
            po_number="PO-2026-0004",
            total_amount=110000,
            bank_account="9999-9999999",
            invoice_date="2026-07-15",
        ),
        "purchase_order": po_fields(po_number="PO-2026-0004", total_amount=110000),
        "goods_receipt": grn_fields(receipt_number="GRN-2026-0004", po_number="PO-2026-0004"),
        "expected": {"recommendation": "REFER_VENDOR_REVIEW", "rule_ids": ["AP-VENDOR-002"]},
    },
    "case-e-grn-mismatch": {
        "invoice": invoice_fields(
            invoice_number="INV-2026-0011",
            po_number="PO-2026-0005",
            total_amount=110000,
            invoice_date="2026-07-15",
        ),
        "purchase_order": po_fields(po_number="PO-2026-0005", total_amount=110000),
        "goods_receipt": grn_fields(
            receipt_number="GRN-2026-0005",
            po_number="PO-2026-0005",
            quantity=60,
        ),
        "expected": {"recommendation": "REFER_GRN_MISMATCH", "rule_ids": ["AP-GRN-001"]},
    },
    "case-f-tax-review": {
        "invoice": invoice_fields(
            invoice_number="INV-2026-0012",
            po_number="PO-2026-0006",
            total_amount=108000,
            invoice_date="2026-07-15",
            subtotal_amount=100000,
            tax_amount=8000,
        ),
        "purchase_order": po_fields(po_number="PO-2026-0006", total_amount=108000),
        "goods_receipt": grn_fields(receipt_number="GRN-2026-0006", po_number="PO-2026-0006"),
        "expected": {"recommendation": "REFER_TAX_REVIEW", "rule_ids": ["AP-TAX-001"]},
    },
}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", "utf-8")


def write_case(base_dir: Path, case_name: str, payload: dict[str, Any]) -> None:
    case_dir = base_dir / case_name
    case_dir.mkdir(parents=True, exist_ok=True)
    for document_type in ("invoice", "purchase_order", "goods_receipt"):
        write_document_pdf(
            case_dir / f"{document_type}.pdf",
            document_type=document_type,
            fields=payload[document_type],
        )


def main() -> None:
    for target in (ROOT_SAMPLES, PACK_SAMPLES):
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)
    if PACK_TESTS.exists():
        shutil.rmtree(PACK_TESTS)
    PACK_TESTS.mkdir(parents=True, exist_ok=True)
    for target in (ROOT_SAMPLES, PACK_SAMPLES):
        for case_name, payload in CASES.items():
            write_case(target, case_name, payload)
    for index, (case_name, payload) in enumerate(CASES.items(), start=1):
        suffix = chr(ord("a") + index - 1)
        write_json(
            PACK_TESTS / f"expected-case-{suffix}.json",
            {
                "case": case_name,
                "recommendation": payload["expected"]["recommendation"],
                "rule_ids": payload["expected"]["rule_ids"],
                "write_performed": False,
            },
        )
    print(f"Generated {len(CASES)} AP fixture cases in {ROOT_SAMPLES}")


if __name__ == "__main__":
    main()
