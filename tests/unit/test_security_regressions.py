from __future__ import annotations

from pathlib import Path

import pytest

from ap_invoice_core.extraction import load_canonical_from_documents
from ap_invoice_core.service import ReviewService
from tests.helpers import PROJECT_ROOT, SAMPLES_DIR, ocr_results_for_case, review_case


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


def test_legacy_start_review_is_disabled_before_sidecar_runtime(tmp_path: Path) -> None:
    service = ReviewService(project_root=PROJECT_ROOT, artifact_root=tmp_path / "artifacts")
    created = service.create_case(tenant_id="test-tenant")

    with pytest.raises(ValueError, match="Legacy sidecar review is disabled"):
        service.start_review(case_id=str(created["case_id"]))


def test_legacy_sidecar_extraction_is_disabled(tmp_path: Path) -> None:
    pdf = tmp_path / "invoice.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    sidecar = tmp_path / "invoice.json"
    sidecar.write_text('{"document_type": "invoice"}', "utf-8")

    with pytest.raises(RuntimeError, match="Legacy sidecar extraction is disabled"):
        load_canonical_from_documents(
            invoice_pdf=pdf,
            purchase_order_pdf=pdf,
            goods_receipt_pdf=pdf,
        )


def test_submit_rejects_post_review_ocr_overwrite(tmp_path: Path) -> None:
    reviewed = review_case("case-a-pay-ready", tmp_path / "artifacts")

    result = reviewed["service"].submit_ocr_result(
        run_id=reviewed["run_id"],
        ocr_results=ocr_results_for_case("case-a-pay-ready"),
    )

    assert result["status"] == "OCR_VALIDATION_FAILED"
    assert result["error_code"] == "RUN_STATE_INVALID"


def test_review_from_ocr_result_rejects_second_review_after_completion(tmp_path: Path) -> None:
    reviewed = review_case("case-a-pay-ready", tmp_path / "artifacts")

    with pytest.raises(ValueError, match="not OCR_VALIDATED"):
        reviewed["service"].review_from_ocr_result(run_id=reviewed["run_id"])


def test_po_not_found_is_referred_not_pay_ready(tmp_path: Path) -> None:
    ocr_results = ocr_results_for_case("case-a-pay-ready")
    ocr_results["invoice"]["fields"]["po_number"] = "PO-DOES-NOT-EXIST"

    result = _review_custom_ocr_results(ocr_results, tmp_path / "artifacts")

    assert result["recommendation"] == "REFER_PO_MISMATCH"
    assert "AP-PO-001" in [rule["rule_id"] for rule in result["rule_results"]]


def test_grn_not_received_is_referred_not_pay_ready(tmp_path: Path) -> None:
    ocr_results = ocr_results_for_case("case-a-pay-ready")
    ocr_results["goods_receipt"]["fields"]["received"] = False

    result = _review_custom_ocr_results(ocr_results, tmp_path / "artifacts")

    assert result["recommendation"] == "REFER_GRN_MISMATCH"
    assert [rule["rule_id"] for rule in result["rule_results"]] == ["AP-GRN-001"]


def _review_custom_ocr_results(
    ocr_results: dict[str, object],
    artifact_root: Path,
) -> dict[str, object]:
    service = ReviewService(project_root=PROJECT_ROOT, artifact_root=artifact_root)
    prepared = service.prepare_ocr_run(
        folder_path=str(SAMPLES_DIR / "case-a-pay-ready"),
        tenant_id="test-tenant",
    )
    submitted = service.submit_ocr_result(run_id=str(prepared["run_id"]), ocr_results=ocr_results)
    assert submitted["status"] == "OCR_VALIDATED"
    return service.review_from_ocr_result(run_id=str(prepared["run_id"]))
