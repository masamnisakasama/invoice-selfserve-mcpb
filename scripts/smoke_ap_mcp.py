from __future__ import annotations

from pathlib import Path

from ap_invoice_core.service import ReviewService


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    workspace = PROJECT_ROOT / ".tmp-workspaces" / "smoke"
    service = ReviewService(
        project_root=PROJECT_ROOT,
        artifact_root=PROJECT_ROOT / "artifacts" / "smoke",
        default_workspace_dir=workspace,
    )
    setup = service.setup_demo_workspace(overwrite=True)
    assert len(setup["cases"]) >= 6
    cases = service.list_demo_cases_with_workspace()["demo_cases"]
    assert len(cases) >= 6
    preview = service.preview_folder(folder_path=str(workspace / "case-a-pay-ready"))
    assert preview["ready_for_review"] is True
    result = service.review_folder(
        folder_path=str(workspace / "case-a-pay-ready"),
        tenant_id="demo-tenant",
    )
    assert result["recommendation"] == "PAY_READY_CANDIDATE"
    assert result["draft_payload"]["write_performed"] is False
    assert result["write_performed"] is False
    brief = service.build_approval_brief(job_id=str(result["job_id"]))
    assert brief["approval_recommendation"] == "approve_candidate"
    print("Smoke passed: setup_demo_workspace/preview_folder/review_folder/build_approval_brief")


if __name__ == "__main__":
    main()
