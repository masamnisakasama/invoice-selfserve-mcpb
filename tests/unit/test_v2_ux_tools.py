from __future__ import annotations

from pathlib import Path

import pytest

from ap_invoice_core.service import ReviewService
from tests.helpers import PROJECT_ROOT, ensure_samples, ocr_results_for_case, review_case


@pytest.fixture
def service(tmp_path: Path) -> ReviewService:
    ensure_samples()
    return ReviewService(
        project_root=PROJECT_ROOT,
        artifact_root=tmp_path / "artifacts",
        default_workspace_dir=PROJECT_ROOT / ".tmp-workspaces" / "unit-default",
    )


EXPECTED_CASES = [
    ("case-a-pay-ready", "PAY_READY_CANDIDATE"),
    ("case-b-po-mismatch", "REFER_PO_MISMATCH"),
    ("case-c-duplicate", "REFER_DUPLICATE_REVIEW"),
    ("case-d-vendor-review", "REFER_VENDOR_REVIEW"),
    ("case-e-grn-mismatch", "REFER_GRN_MISMATCH"),
    ("case-f-tax-review", "REFER_TAX_REVIEW"),
]


def test_list_demo_cases_returns_demo_cases(service: ReviewService) -> None:
    cases = service.list_demo_cases()["demo_cases"]
    assert [case["case_id"] for case in cases] == [case_id for case_id, _ in EXPECTED_CASES]
    assert cases[0]["expected_recommendation"] == "PAY_READY_CANDIDATE"
    assert all(case["business_value_ja"] for case in cases)
    assert all(case["case_dir"] for case in cases)


def test_setup_demo_workspace_exports_pdf_only_visible_files(service: ReviewService) -> None:
    workspace = PROJECT_ROOT / ".tmp-workspaces" / "unit-visible"
    result = service.setup_demo_workspace(workspace_dir=str(workspace), overwrite=True)

    assert result["workspace_dir"] == str(workspace.resolve())
    assert len(result["cases"]) == len(EXPECTED_CASES)
    for case_id, _ in EXPECTED_CASES:
        case_dir = workspace / case_id
        assert (case_dir / "invoice.pdf").is_file()
        assert (case_dir / "purchase_order.pdf").is_file()
        assert (case_dir / "goods_receipt.pdf").is_file()
        assert not list(case_dir.glob("*.json"))


def test_preview_folder_detects_three_pdfs_without_sidecars(service: ReviewService) -> None:
    workspace = PROJECT_ROOT / ".tmp-workspaces" / "unit-preview"
    service.setup_demo_workspace(workspace_dir=str(workspace), overwrite=True)

    preview = service.preview_folder(folder_path=str(workspace / "case-b-po-mismatch"))

    assert preview["ready_for_review"] is True
    assert [doc["document_type"] for doc in preview["detected_documents"]] == [
        "invoice",
        "purchase_order",
        "goods_receipt",
    ]
    assert all("sidecar_path" not in doc for doc in preview["detected_documents"])


@pytest.mark.parametrize("case_id", [case_id for case_id, _ in EXPECTED_CASES])
def test_review_demo_case_prepares_ocr_run(case_id: str, service: ReviewService) -> None:
    result = service.review_demo_case(case_id=case_id, tenant_id="demo-tenant")

    assert result["status"] == "OCR_PREPARED"
    assert result["run_id"].startswith("ocr-run-")
    assert result["structured_content"]["next_tool"] == "ap_invoice_submit_ocr_result"
    assert len([part for part in result["content_parts"] if part["type"] == "image"]) == 3


def test_review_demo_case_accepts_short_alias(service: ReviewService) -> None:
    result = service.review_demo_case(case_id="case-a", tenant_id="demo-tenant")

    assert result["status"] == "OCR_PREPARED"
    assert result["folder_path"].endswith("case-a-pay-ready")


@pytest.mark.parametrize(
    ("case_id", "expected"),
    EXPECTED_CASES,
)
def test_ocr_e2e_review_cases(case_id: str, expected: str, tmp_path: Path) -> None:
    result = review_case(case_id, tmp_path / "artifacts")["result"]

    assert result["status"] == "REVIEW_COMPLETED"
    assert result["recommendation"] == expected
    assert result["draft_payload_summary"]["write_performed"] is False
    assert result["write_performed"] is False
    assert result["artifact_paths"]["ocr_results"]


def test_prepare_ocr_run_rejects_json_sidecars(service: ReviewService) -> None:
    workspace = PROJECT_ROOT / ".tmp-workspaces" / "unit-json-sidecar"
    service.setup_demo_workspace(workspace_dir=str(workspace), overwrite=True)
    (workspace / "case-a-pay-ready" / "invoice.json").write_text("{}", "utf-8")

    result = service.review_folder(folder_path=str(workspace / "case-a-pay-ready"))

    assert result["status"] == "BLOCKED_INPUT_SIDECAR_JSON"
    assert result["error_code"] == "INPUT_SIDECAR_JSON_FORBIDDEN"
    assert "invoice.json" in result["forbidden_files"]
    assert result["write_performed"] is False


def test_review_folder_missing_po_fails_clearly(service: ReviewService) -> None:
    workspace = PROJECT_ROOT / ".tmp-workspaces" / "unit-missing-po"
    service.setup_demo_workspace(workspace_dir=str(workspace), overwrite=True)
    (workspace / "case-a-pay-ready" / "purchase_order.pdf").unlink()

    result = service.review_folder(folder_path=str(workspace / "case-a-pay-ready"))

    assert result["status"] == "BLOCKED_REQUIRED_DOCUMENTS_MISSING"
    assert result["error_code"] == "REQUIRED_DOCUMENTS_MISSING"
    assert "purchase_order" in result["missing_document_types"]
    assert result["write_performed"] is False


def test_submit_ocr_result_validates_required_fields(service: ReviewService) -> None:
    workspace = PROJECT_ROOT / ".tmp-workspaces" / "unit-ocr-validation"
    service.setup_demo_workspace(workspace_dir=str(workspace), overwrite=True)
    prepared = service.prepare_ocr_run(folder_path=str(workspace / "case-a-pay-ready"))
    ocr_results = ocr_results_for_case("case-a-pay-ready")
    del ocr_results["invoice"]["fields"]["total_amount"]

    result = service.submit_ocr_result(run_id=str(prepared["run_id"]), ocr_results=ocr_results)

    assert result["status"] == "OCR_VALIDATION_FAILED"
    assert result["error_code"] == "OCR_REQUIRED_FIELD_MISSING"
    assert "invoice.total_amount" in result["missing_fields"]


def test_submit_ocr_result_saves_to_runs_and_not_input_folder(service: ReviewService) -> None:
    workspace = PROJECT_ROOT / ".tmp-workspaces" / "unit-ocr-save"
    service.setup_demo_workspace(workspace_dir=str(workspace), overwrite=True)
    folder = workspace / "case-a-pay-ready"
    prepared = service.prepare_ocr_run(folder_path=str(folder))

    result = service.submit_ocr_result(
        run_id=str(prepared["run_id"]),
        ocr_results=ocr_results_for_case("case-a-pay-ready"),
    )

    assert result["status"] == "OCR_VALIDATED"
    assert Path(result["ocr_result_paths"]["invoice"]).is_file()
    assert "_runs" in result["ocr_result_paths"]["invoice"]
    assert not list(folder.glob("*.json"))


def test_review_demo_case_unknown_case_fails(service: ReviewService) -> None:
    with pytest.raises(ValueError, match="Unknown demo case"):
        service.review_demo_case(case_id="case-z", tenant_id="demo-tenant")
