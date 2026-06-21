from __future__ import annotations

from pathlib import Path

from ap_invoice_core.service import ReviewService


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    service = ReviewService(project_root=PROJECT_ROOT, artifact_root=PROJECT_ROOT / "artifacts" / "smoke")
    created = service.create_case(tenant_id="demo-tenant", case_label="smoke case-a")
    case_id = created["case_id"]
    sample_dir = PROJECT_ROOT / "samples" / "case-a-pay-ready"
    for document_type in ("invoice", "purchase_order", "goods_receipt"):
        service.upload_document(
            case_id=case_id,
            document_type=document_type,
            file_path=str(sample_dir / f"{document_type}.pdf"),
        )
    started = service.start_review(case_id=case_id)
    result = service.get_review_result(job_id=started["job_id"])["result"]
    assert result["recommendation"] == "PAY_READY_CANDIDATE"
    draft = service.build_draft_payload(case_id=case_id, target_system="generic_ap")
    assert draft["write_performed"] is False
    print("Smoke passed: create/upload/start/get/draft case-a")


if __name__ == "__main__":
    main()
