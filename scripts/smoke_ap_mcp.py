from __future__ import annotations

from pathlib import Path
from typing import Any

from ap_invoice_core.service import ReviewService


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    workspace = PROJECT_ROOT / ".tmp-workspaces" / "smoke"
    service = ReviewService(
        project_root=PROJECT_ROOT,
        artifact_root=PROJECT_ROOT / "artifacts" / "smoke",
        default_workspace_dir=workspace,
    )
    setup = service.setup_demo_workspace(overwrite=True)
    assert len(setup["cases"]) >= 6
    cases = service.list_demo_cases_with_workspace()["demo_cases"]
    assert len(cases) >= 6
    preview = service.preview_folder(folder_path=str(workspace / "case-a-pay-ready"))
    assert preview["ready_for_review"] is True
    result = service.review_folder(
        folder_path=str(workspace / "case-a-pay-ready"),
        tenant_id="demo-tenant",
    )
    assert result["status"] == "OCR_PREPARED"
    submitted = service.submit_ocr_result(
        run_id=str(result["run_id"]),
        ocr_results=_ocr_results_for_case("case-a-pay-ready"),
    )
    assert submitted["status"] == "OCR_VALIDATED"
    result = service.review_from_ocr_result(run_id=str(result["run_id"]))
    assert result["recommendation"] == "PAY_READY_CANDIDATE"
    assert result["draft_payload"]["write_performed"] is False
    assert result["write_performed"] is False
    brief = service.build_completed_ocr_approval_brief(run_id=str(result["run_id"]))
    assert brief["approval_recommendation"] == "approve_candidate"
    print("Smoke passed: setup_demo_workspace/preview_folder/OCR review/approval_brief")


def _ocr_results_for_case(case_name: str) -> dict[str, Any]:
    if case_name != "case-a-pay-ready":
        raise ValueError(f"Unsupported smoke case: {case_name}")
    payload = {
        "invoice": {
            "invoice_number": "INV-2026-0008",
            "invoice_date": "2026-07-15",
            "due_date": "2026-08-14",
            "vendor_name": "Tokyo Office Supply Co.",
            "vendor_id": "V-1001",
            "po_number": "PO-2026-0001",
            "currency": "JPY",
            "subtotal_amount": 100000,
            "tax_amount": 10000,
            "total_amount": 110000,
            "bank_account": "0001-1234567",
            "tax_code": "JP10",
            "cost_center": "CC-ADMIN",
            "line_items": [
                {
                    "description": "Office supplies bundle",
                    "quantity": 100,
                    "unit_price": 1000,
                    "amount": 100000,
                    "tax_code": "JP10",
                }
            ],
        },
        "purchase_order": {
            "po_number": "PO-2026-0001",
            "vendor_id": "V-1001",
            "currency": "JPY",
            "total_amount": 110000,
            "approved": True,
            "remaining_balance": 110000,
            "line_items": [
                {
                    "description": "Office supplies bundle",
                    "quantity": 100,
                    "unit_price": 1000,
                    "amount": 100000,
                    "tax_code": "JP10",
                }
            ],
        },
        "goods_receipt": {
            "receipt_number": "GRN-2026-0001",
            "po_number": "PO-2026-0001",
            "received": True,
            "received_quantity": 100,
            "receipt_date": "2026-06-18",
        },
    }
    return {
        document_type: {
            "document_type": document_type,
            "document_name": f"{document_type}.pdf",
            "fields": payload[document_type],
            "evidence": [
                {
                    "page": 1,
                    "field_label": "Total",
                    "raw_text": "Smoke OCR fixture",
                }
            ],
        }
        for document_type in ("invoice", "purchase_order", "goods_receipt")
    }


if __name__ == "__main__":
    main()
