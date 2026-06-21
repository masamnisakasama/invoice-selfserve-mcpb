from __future__ import annotations

from pathlib import Path

import pytest

from ap_invoice_core.service import ReviewService
from tests.helpers import PROJECT_ROOT, SAMPLES_DIR, ensure_samples


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


@pytest.mark.parametrize(
    ("case_id", "expected"),
    EXPECTED_CASES,
)
def test_review_demo_cases(case_id: str, expected: str, service: ReviewService) -> None:
    result = service.review_demo_case(case_id=case_id, tenant_id="demo-tenant")

    assert result["demo_case_id"] == case_id
    assert result["recommendation"] == expected
    assert result["write_performed"] is False
    assert result["draft_payload"]["write_performed"] is False
    assert result["next_actions_ja"]
    assert "This demo requires sidecar JSON" in result["demo_note"]


def test_review_demo_case_accepts_short_alias(service: ReviewService) -> None:
    result = service.review_demo_case(case_id="case-a", tenant_id="demo-tenant")

    assert result["demo_case_id"] == "case-a-pay-ready"
    assert result["recommendation"] == "PAY_READY_CANDIDATE"


def test_setup_demo_workspace_exports_visible_files(service: ReviewService) -> None:
    workspace = PROJECT_ROOT / ".tmp-workspaces" / "unit-visible"
    result = service.setup_demo_workspace(workspace_dir=str(workspace), overwrite=True)

    assert result["workspace_dir"] == str(workspace.resolve())
    assert len(result["cases"]) == len(EXPECTED_CASES)
    for case_id, _ in EXPECTED_CASES:
        case_dir = workspace / case_id
        assert (case_dir / "invoice.pdf").is_file()
        assert (case_dir / "invoice.json").is_file()
        assert (case_dir / "purchase_order.pdf").is_file()
        assert (case_dir / "purchase_order.json").is_file()
        assert (case_dir / "goods_receipt.pdf").is_file()
        assert (case_dir / "goods_receipt.json").is_file()


def test_preview_folder_returns_key_fields(service: ReviewService) -> None:
    workspace = PROJECT_ROOT / ".tmp-workspaces" / "unit-preview"
    service.setup_demo_workspace(workspace_dir=str(workspace), overwrite=True)

    preview = service.preview_folder(folder_path=str(workspace / "case-b-po-mismatch"))

    assert preview["ready_for_review"] is True
    assert [doc["document_type"] for doc in preview["detected_documents"]] == [
        "invoice",
        "purchase_order",
        "goods_receipt",
    ]
    invoice = preview["detected_documents"][0]
    assert invoice["key_fields"]["invoice_number"] == "INV-2026-0009"
    assert invoice["key_fields"]["total_amount"] == 121000


@pytest.mark.parametrize(
    ("case_id", "expected"),
    EXPECTED_CASES,
)
def test_review_folder_cases(case_id: str, expected: str, service: ReviewService) -> None:
    workspace = PROJECT_ROOT / ".tmp-workspaces" / "unit-review-folder"
    service.setup_demo_workspace(workspace_dir=str(workspace), overwrite=True)

    result = service.review_folder(folder_path=str(workspace / case_id), tenant_id="demo-tenant")

    assert result["folder_path"] == str((workspace / case_id).resolve())
    assert result["recommendation"] == expected
    assert result["detected_documents"]
    assert result["draft_payload_summary"]["write_performed"] is False
    assert result["write_performed"] is False


def test_review_folder_missing_po_fails_clearly(service: ReviewService) -> None:
    workspace = PROJECT_ROOT / ".tmp-workspaces" / "unit-missing-po"
    service.setup_demo_workspace(workspace_dir=str(workspace), overwrite=True)
    (workspace / "case-a-pay-ready" / "purchase_order.pdf").unlink()

    result = service.review_folder(folder_path=str(workspace / "case-a-pay-ready"))

    assert result["status"] == "blocked"
    assert result["error_code"] == "REQUIRED_DOCUMENTS_MISSING"
    assert "purchase_order" in result["missing_document_types"]
    assert result["write_performed"] is False


def test_review_folder_missing_sidecar_fails_clearly(service: ReviewService) -> None:
    workspace = PROJECT_ROOT / ".tmp-workspaces" / "unit-missing-sidecar"
    service.setup_demo_workspace(workspace_dir=str(workspace), overwrite=True)
    (workspace / "case-a-pay-ready" / "invoice.json").unlink()

    result = service.review_folder(folder_path=str(workspace / "case-a-pay-ready"))

    assert result["status"] == "blocked"
    assert result["error_code"] == "DOCUMENT_VALIDATION_FAILED"
    assert any("missing sidecar JSON" in error for error in result["validation_errors"])
    assert result["write_performed"] is False


def test_review_demo_case_unknown_case_fails(service: ReviewService) -> None:
    with pytest.raises(ValueError, match="Unknown demo case"):
        service.review_demo_case(case_id="case-z", tenant_id="demo-tenant")


def test_review_invoice_packet_requires_three_pdfs(service: ReviewService) -> None:
    sample = SAMPLES_DIR / "case-a-pay-ready"

    with pytest.raises(FileNotFoundError):
        service.review_invoice_packet_from_paths(
            tenant_id="demo-tenant",
            invoice_path=str(sample / "invoice.pdf"),
            purchase_order_path=str(sample / "purchase_order.pdf"),
            goods_receipt_path=str(sample / "missing.pdf"),
        )


def test_explain_exception_po_mismatch(service: ReviewService) -> None:
    result = service.review_demo_case(case_id="case-b-po-mismatch", tenant_id="demo-tenant")
    explanation = service.explain_exception(job_id=str(result["job_id"]), audience="ap_operator")

    assert explanation["recommendation"] == "REFER_PO_MISMATCH"
    assert explanation["rule_ids"] == ["AP-PO-001"]
    assert explanation["root_causes"][0]["rule_id"] == "AP-PO-001"
    assert explanation["next_actions_ja"]
    assert explanation["write_performed"] is False


def test_build_approval_brief_pay_ready(service: ReviewService) -> None:
    result = service.review_demo_case(case_id="case-a-pay-ready", tenant_id="demo-tenant")
    brief = service.build_approval_brief(job_id=str(result["job_id"]))

    assert brief["approval_recommendation"] == "approve_candidate"
    assert brief["recommendation"] == "PAY_READY_CANDIDATE"
    assert brief["write_performed"] is False


def test_build_approval_brief_duplicate_hold(service: ReviewService) -> None:
    result = service.review_demo_case(case_id="case-c-duplicate", tenant_id="demo-tenant")
    brief = service.build_approval_brief(job_id=str(result["job_id"]))

    assert brief["approval_recommendation"] == "hold"
    assert brief["recommendation"] == "REFER_DUPLICATE_REVIEW"
    assert brief["rule_ids"] == ["AP-DUP-001"]
    assert brief["write_performed"] is False
