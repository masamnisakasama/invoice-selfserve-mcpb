from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ap_invoice_core.service import ReviewService
from scripts.generate_ap_samples import CASES as SAMPLE_CASES
from scripts.generate_ap_samples import main as generate_samples


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLES_DIR = PROJECT_ROOT / "samples"


def ensure_samples() -> None:
    generate_samples()


def load_expected(case_name: str) -> dict[str, Any]:
    ensure_samples()
    payload = SAMPLE_CASES[case_name]
    return {
        "case": case_name,
        "recommendation": payload["expected"]["recommendation"],
        "rule_ids": payload["expected"]["rule_ids"],
        "write_performed": False,
    }


def ocr_results_for_case(case_name: str) -> dict[str, Any]:
    payload = SAMPLE_CASES[case_name]
    return {
        document_type: {
            "document_type": document_type,
            "document_name": f"{document_type}.pdf",
            "fields": json.loads(json.dumps(payload[document_type])),
            "evidence": _evidence_for(document_type, payload[document_type]),
        }
        for document_type in ("invoice", "purchase_order", "goods_receipt")
    }


def review_case(case_name: str, artifact_root: Path) -> dict[str, Any]:
    ensure_samples()
    service = ReviewService(
        project_root=PROJECT_ROOT,
        artifact_root=artifact_root,
        default_workspace_dir=PROJECT_ROOT / ".tmp-workspaces" / f"helper-{case_name}",
    )
    case_dir = SAMPLES_DIR / case_name
    prepared = service.prepare_ocr_run(
        folder_path=str(case_dir),
        tenant_id="test-tenant",
        target_system="generic_ap",
    )
    submitted = service.submit_ocr_result(
        run_id=str(prepared["run_id"]),
        ocr_results=ocr_results_for_case(case_name),
    )
    result = service.review_from_ocr_result(run_id=str(prepared["run_id"]), target_system="generic_ap")
    draft = {"payload": result["draft_payload"], "write_performed": False}
    return {
        "service": service,
        "case_id": prepared["run_id"],
        "run_id": prepared["run_id"],
        "prepared": prepared,
        "submitted": submitted,
        "result": result,
        "draft": draft,
    }


def _evidence_for(document_type: str, fields: dict[str, Any]) -> list[dict[str, Any]]:
    if document_type == "invoice":
        return [
            {
                "page": 1,
                "field_label": "Total",
                "raw_text": f"Total: JPY {fields['total_amount']:,}",
            }
        ]
    if document_type == "purchase_order":
        return [
            {
                "page": 1,
                "field_label": "Total",
                "raw_text": f"Total: JPY {fields['total_amount']:,}",
            }
        ]
    return [
        {
            "page": 1,
            "field_label": "Received Quantity",
            "raw_text": f"Received Quantity: {fields['received_quantity']}",
        }
    ]
