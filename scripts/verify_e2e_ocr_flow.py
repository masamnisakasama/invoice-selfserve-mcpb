from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from ap_invoice_core.service import ReviewService
from generate_ap_samples import CASES, main as generate_samples


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = PROJECT_ROOT / ".tmp-workspaces" / "verify-e2e-ocr-flow"
DOCUMENT_TYPES = ("invoice", "purchase_order", "goods_receipt")


def main() -> None:
    failures: list[str] = []
    generate_samples()
    if WORKSPACE.exists():
        shutil.rmtree(WORKSPACE)

    service = ReviewService(
        project_root=PROJECT_ROOT,
        artifact_root=PROJECT_ROOT / "artifacts" / "verify-e2e-ocr-flow",
        default_workspace_dir=WORKSPACE,
    )
    setup = service.setup_demo_workspace(overwrite=True)
    _expect(setup["write_performed"] is False, "setup must be draft/no-write", failures)
    _expect(len(setup["cases"]) == len(CASES), "setup must export all demo cases", failures)

    listed = service.list_demo_cases_with_workspace()
    _expect(listed["workspace_initialized"] is True, "workspace must be initialized", failures)
    _expect(len(listed["demo_cases"]) == len(CASES), "list must show all demo cases", failures)

    for case_id, payload in CASES.items():
        case_dir = WORKSPACE / case_id
        _expect(not list(case_dir.glob("*.json")), f"{case_id}: input folder must be PDF-only", failures)
        _expect(all((case_dir / f"{doc}.pdf").is_file() for doc in DOCUMENT_TYPES), f"{case_id}: PDFs missing", failures)

        if case_id == "case-a-pay-ready":
            prepared = service.review_demo_case(case_id="case-a", tenant_id="verify-tenant")
        elif case_id == "case-b-po-mismatch":
            prepared = service.review_folder(folder_path=str(case_dir), tenant_id="verify-tenant")
        else:
            prepared = service.prepare_ocr_run(folder_path=str(case_dir), tenant_id="verify-tenant")

        _expect(prepared["status"] == "OCR_PREPARED", f"{case_id}: prepare status", failures)
        _expect(prepared["structured_content"]["next_tool"] == "ap_invoice_submit_ocr_result", f"{case_id}: next submit tool", failures)
        _expect(_image_count(prepared) == 3, f"{case_id}: expected three OCR images", failures)

        submitted = service.submit_ocr_result(
            run_id=str(prepared["run_id"]),
            ocr_results=_ocr_results_for_case(case_id),
        )
        _expect(submitted["status"] == "OCR_VALIDATED", f"{case_id}: submit status", failures)
        _expect(submitted["next_tool"] == "ap_invoice_review_from_ocr_result", f"{case_id}: next review tool", failures)

        result = service.review_from_ocr_result(run_id=str(prepared["run_id"]))
        _expect(result["status"] == "REVIEW_COMPLETED", f"{case_id}: review status", failures)
        _expect(result["recommendation"] == payload["expected"]["recommendation"], f"{case_id}: recommendation", failures)
        _expect(result["rule_ids"] == payload["expected"]["rule_ids"], f"{case_id}: rule ids", failures)
        _expect(result["write_performed"] is False, f"{case_id}: review write_performed", failures)
        _expect(result["draft_payload_summary"]["write_performed"] is False, f"{case_id}: draft write_performed", failures)
        _expect("_runs" in result["artifact_paths"]["ocr_results"], f"{case_id}: OCR path under _runs", failures)
        _expect(Path(result["artifact_paths"]["decision_result"]).is_file(), f"{case_id}: decision artifact", failures)
        _expect(not list(case_dir.glob("*.json")), f"{case_id}: no input JSON after review", failures)

        explain = service.explain_completed_ocr_review(run_id=str(prepared["run_id"]))
        brief = service.build_completed_ocr_approval_brief(run_id=str(prepared["run_id"]))
        _expect(explain["write_performed"] is False, f"{case_id}: explain write_performed", failures)
        _expect(brief["write_performed"] is False, f"{case_id}: brief write_performed", failures)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        raise SystemExit(1)
    print("E2E OCR flow check passed: setup/list/prepare/OCR-submit/review/explain/brief for case-a through case-f.")


def _ocr_results_for_case(case_id: str) -> dict[str, Any]:
    payload = CASES[case_id]
    return {
        document_type: {
            "document_type": document_type,
            "document_name": f"{document_type}.pdf",
            "fields": json.loads(json.dumps(payload[document_type])),
            "evidence": _evidence_for(document_type, payload[document_type]),
        }
        for document_type in DOCUMENT_TYPES
    }


def _evidence_for(document_type: str, fields: dict[str, Any]) -> list[dict[str, Any]]:
    if document_type in {"invoice", "purchase_order"}:
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


def _image_count(prepared: dict[str, Any]) -> int:
    return sum(1 for part in prepared["content_parts"] if part["type"] == "image")


def _expect(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


if __name__ == "__main__":
    main()
