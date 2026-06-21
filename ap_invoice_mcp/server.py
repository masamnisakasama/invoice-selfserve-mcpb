from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from ap_invoice_core.engine import RULESET_VERSION, WORKFLOW_PACK
from ap_invoice_core.service import ReviewService


def _default_project_root() -> Path:
    source_root = Path(__file__).resolve().parents[1]
    if (source_root / "workflow-packs" / WORKFLOW_PACK).is_dir():
        return source_root
    return Path.cwd()


service = ReviewService(project_root=_default_project_root())
mcp = FastMCP("AP Invoice Exception Review MCPB")


@mcp.tool()
def create_ap_review_case(
    tenant_id: str,
    workflow_pack: str = WORKFLOW_PACK,
    ruleset_version: str = RULESET_VERSION,
    case_label: str = "",
) -> dict[str, Any]:
    """Create an AP invoice review case and return required upload slots."""
    return service.create_case(
        tenant_id=tenant_id,
        workflow_pack=workflow_pack,
        ruleset_version=ruleset_version,
        case_label=case_label,
    )


@mcp.tool()
def upload_ap_document(case_id: str, document_type: str, file_path: str) -> dict[str, Any]:
    """Attach a local invoice, purchase order, or goods receipt PDF to a case."""
    return service.upload_document(
        case_id=case_id,
        document_type=document_type,
        file_path=file_path,
    )


@mcp.tool()
def start_ap_invoice_review(case_id: str) -> dict[str, Any]:
    """Run deterministic AP 3-way match, duplicate, vendor, and tax checks."""
    return service.start_review(case_id=case_id)


@mcp.tool()
def get_ap_invoice_review_result(job_id: str) -> dict[str, Any]:
    """Return a completed AP review decision packet with evidence and artifacts."""
    return service.get_review_result(job_id=job_id)


@mcp.tool()
def build_erp_draft_payload(
    case_id: str,
    target_system: str,
    mode: str = "draft_only",
) -> dict[str, Any]:
    """Build a draft-only ERP/SaaS payload. External writes are never performed."""
    return service.build_draft_payload(
        case_id=case_id,
        target_system=target_system,
        mode=mode,
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
