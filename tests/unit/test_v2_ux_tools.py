from __future__ import annotations

from pathlib import Path

import pytest

from ap_invoice_core.service import ReviewService
from tests.helpers import PROJECT_ROOT, SAMPLES_DIR, ensure_samples


@pytest.fixture
def service(tmp_path: Path) -> ReviewService:
    ensure_samples()
    return ReviewService(project_root=PROJECT_ROOT, artifact_root=tmp_path / "artifacts")


def test_list_demo_cases_returns_four_cases(service: ReviewService) -> None:
    cases = service.list_demo_cases()["demo_cases"]
    assert [case["case_id"] for case in cases] == [
        "case-a-pay-ready",
        "case-b-po-mismatch",
        "case-c-duplicate",
        "case-d-vendor-review",
    ]
    assert cases[0]["expected_recommendation"] == "PAY_READY_CANDIDATE"
    assert all(case["business_value_ja"] for case in cases)


@pytest.mark.parametrize(
    ("case_id", "expected"),
    [
        ("case-a-pay-ready", "PAY_READY_CANDIDATE"),
        ("case-b-po-mismatch", "REFER_PO_MISMATCH"),
        ("case-c-duplicate", "REFER_DUPLICATE_REVIEW"),
        ("case-d-vendor-review", "REFER_VENDOR_REVIEW"),
    ],
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
