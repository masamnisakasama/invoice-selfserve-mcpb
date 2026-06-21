from __future__ import annotations

import json
import shutil
from datetime import date, timedelta
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROOT_SAMPLES = PROJECT_ROOT / "samples"
PACK_SAMPLES = PROJECT_ROOT / "workflow-packs" / "ap-invoice-v1" / "samples"
PACK_TESTS = PROJECT_ROOT / "workflow-packs" / "ap-invoice-v1" / "tests"


PDF_BYTES = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 54 >>
stream
BT /F1 12 Tf 36 96 Td (AP Invoice MCPB demo fixture) Tj ET
endstream
endobj
trailer
<< /Root 1 0 R >>
%%EOF
"""


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
            quantity=50,
        ),
        "expected": {"recommendation": "REFER_GRN_MISMATCH", "rule_ids": ["AP-GRN-001"]},
    },
    "case-f-tax-review": {
        "invoice": invoice_fields(
            invoice_number="INV-2026-0012",
            po_number="PO-2026-0006",
            total_amount=110000,
            invoice_date="2026-07-15",
            subtotal_amount=100000,
            tax_amount=9000,
        ),
        "purchase_order": po_fields(po_number="PO-2026-0006", total_amount=110000),
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
        (case_dir / f"{document_type}.pdf").write_bytes(PDF_BYTES)
        write_json(
            case_dir / f"{document_type}.json",
            {"document_type": document_type, "fields": payload[document_type]},
        )
    expected = {
        "case": case_name,
        "recommendation": payload["expected"]["recommendation"],
        "rule_ids": payload["expected"]["rule_ids"],
        "write_performed": False,
    }
    write_json(case_dir / "expected-result.json", expected)


def main() -> None:
    for target in (ROOT_SAMPLES, PACK_SAMPLES):
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)
        for case_name, payload in CASES.items():
            write_case(target, case_name, payload)
    PACK_TESTS.mkdir(parents=True, exist_ok=True)
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
