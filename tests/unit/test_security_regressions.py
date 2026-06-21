from __future__ import annotations

import json
from pathlib import Path

import pytest

from ap_invoice_core.service import ReviewService
from scripts.generate_ap_samples import main as generate_samples
from tests.helpers import PROJECT_ROOT, SAMPLES_DIR, review_case


def test_upload_rejects_paths_outside_demo_samples(tmp_path: Path) -> None:
    service = ReviewService(project_root=PROJECT_ROOT, artifact_root=tmp_path / "artifacts")
    created = service.create_case(tenant_id="test-tenant")
    outside_pdf = tmp_path / "invoice.pdf"
    outside_pdf.write_bytes(b"%PDF-1.4\n")

    with pytest.raises(PermissionError, match="demo sample directories"):
        service.upload_document(
            case_id=created["case_id"],
            document_type="invoice",
            file_path=str(outside_pdf),
        )


def test_upload_rejects_post_review_document_overwrite(tmp_path: Path) -> None:
    reviewed = review_case("case-a-pay-ready", tmp_path / "artifacts")

    with pytest.raises(ValueError, match="already completed"):
        reviewed["service"].upload_document(
            case_id=reviewed["case_id"],
            document_type="invoice",
            file_path=str(SAMPLES_DIR / "case-a-pay-ready" / "invoice.pdf"),
        )


def test_start_review_is_idempotent_after_completion(tmp_path: Path) -> None:
    reviewed = review_case("case-a-pay-ready", tmp_path / "artifacts")
    second = reviewed["service"].start_review(case_id=reviewed["case_id"])

    assert second["job_id"] == reviewed["job"]["job_id"]
    assert second["status"] == "completed"


def test_po_not_found_is_referred_not_pay_ready(tmp_path: Path) -> None:
    case_dir = _copy_case(tmp_path, "case-a-pay-ready")
    invoice_path = case_dir / "invoice.json"
    invoice = json.loads(invoice_path.read_text("utf-8"))
    invoice["fields"]["po_number"] = "PO-DOES-NOT-EXIST"
    invoice_path.write_text(json.dumps(invoice, ensure_ascii=False, indent=2), "utf-8")

    result = _review_custom_case(case_dir, tmp_path / "artifacts")

    assert result["recommendation"] == "REFER_PO_MISMATCH"
    assert "AP-PO-001" in [rule["rule_id"] for rule in result["rule_results"]]


def test_grn_not_received_is_referred_not_pay_ready(tmp_path: Path) -> None:
    case_dir = _copy_case(tmp_path, "case-a-pay-ready")
    grn_path = case_dir / "goods_receipt.json"
    grn = json.loads(grn_path.read_text("utf-8"))
    grn["fields"]["received"] = False
    grn_path.write_text(json.dumps(grn, ensure_ascii=False, indent=2), "utf-8")

    result = _review_custom_case(case_dir, tmp_path / "artifacts")

    assert result["recommendation"] == "REFER_GRN_MISMATCH"
    assert [rule["rule_id"] for rule in result["rule_results"]] == ["AP-GRN-001"]


def _copy_case(tmp_path: Path, case_name: str) -> Path:
    generate_samples()
    source = SAMPLES_DIR / case_name
    target = PROJECT_ROOT / "samples" / f"tmp-security-{tmp_path.name}"
    if target.exists():
        for child in target.iterdir():
            child.unlink()
    else:
        target.mkdir(parents=True)
    for child in source.iterdir():
        (target / child.name).write_bytes(child.read_bytes())
    return target


def _review_custom_case(case_dir: Path, artifact_root: Path) -> dict[str, object]:
    service = ReviewService(project_root=PROJECT_ROOT, artifact_root=artifact_root)
    created = service.create_case(tenant_id="test-tenant", case_label=case_dir.name)
    case_id = created["case_id"]
    for document_type in ("invoice", "purchase_order", "goods_receipt"):
        service.upload_document(
            case_id=case_id,
            document_type=document_type,
            file_path=str(case_dir / f"{document_type}.pdf"),
        )
    started = service.start_review(case_id=case_id)
    return service.get_review_result(job_id=started["job_id"])["result"]
