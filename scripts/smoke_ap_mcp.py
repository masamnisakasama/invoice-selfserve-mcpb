from __future__ import annotations

from pathlib import Path

from ap_invoice_core.service import ReviewService


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    service = ReviewService(project_root=PROJECT_ROOT, artifact_root=PROJECT_ROOT / "artifacts" / "smoke")
    cases = service.list_demo_cases()["demo_cases"]
    assert len(cases) == 4
    result = service.review_demo_case(case_id="case-a-pay-ready", tenant_id="demo-tenant")
    assert result["recommendation"] == "PAY_READY_CANDIDATE"
    assert result["draft_payload"]["write_performed"] is False
    assert result["write_performed"] is False
    brief = service.build_approval_brief(job_id=str(result["job_id"]))
    assert brief["approval_recommendation"] == "approve_candidate"
    print("Smoke passed: list_ap_demo_cases/review_ap_demo_case/build_ap_approval_brief")


if __name__ == "__main__":
    main()
