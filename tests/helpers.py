from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ap_invoice_core.service import ReviewService
from scripts.generate_ap_samples import main as generate_samples


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLES_DIR = PROJECT_ROOT / "samples"


def ensure_samples() -> None:
    generate_samples()


def load_expected(case_name: str) -> dict[str, Any]:
    ensure_samples()
    return json.loads((SAMPLES_DIR / case_name / "expected-result.json").read_text("utf-8"))


def review_case(case_name: str, artifact_root: Path) -> dict[str, Any]:
    ensure_samples()
    service = ReviewService(project_root=PROJECT_ROOT, artifact_root=artifact_root)
    created = service.create_case(tenant_id="test-tenant", case_label=case_name)
    case_id = created["case_id"]
    case_dir = SAMPLES_DIR / case_name
    for document_type in ("invoice", "purchase_order", "goods_receipt"):
        service.upload_document(
            case_id=case_id,
            document_type=document_type,
            file_path=str(case_dir / f"{document_type}.pdf"),
        )
    started = service.start_review(case_id=case_id)
    result = service.get_review_result(job_id=started["job_id"])["result"]
    draft = service.build_draft_payload(case_id=case_id, target_system="generic_ap")
    return {"service": service, "case_id": case_id, "job": started, "result": result, "draft": draft}
