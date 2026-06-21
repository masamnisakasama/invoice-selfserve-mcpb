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
def list_ap_demo_cases() -> dict[str, Any]:
    """List bundled AP invoice demo cases and explain their business value."""
    return service.list_demo_cases()


@mcp.tool()
def review_ap_demo_case(
    case_id: str,
    tenant_id: str = "demo-tenant",
    target_system: str = "generic_ap",
) -> dict[str, Any]:
    """Run a bundled AP invoice demo case end-to-end and return a decision packet."""
    return service.review_demo_case(
        case_id=case_id,
        tenant_id=tenant_id,
        target_system=target_system,
    )


@mcp.tool()
def review_ap_invoice_packet(
    tenant_id: str,
    invoice_path: str,
    purchase_order_path: str,
    goods_receipt_path: str,
    case_label: str = "",
    target_system: str = "generic_ap",
) -> dict[str, Any]:
    """Review an invoice, purchase order, and goods receipt packet end-to-end."""
    return service.review_invoice_packet_from_paths(
        tenant_id=tenant_id,
        invoice_path=invoice_path,
        purchase_order_path=purchase_order_path,
        goods_receipt_path=goods_receipt_path,
        case_label=case_label,
        target_system=target_system,
    )


@mcp.tool()
def explain_ap_exception(job_id: str, audience: str = "ap_operator") -> dict[str, Any]:
    """Explain AP review exceptions with evidence, rule IDs, and next actions."""
    return service.explain_exception(job_id=job_id, audience=audience)


@mcp.tool()
def build_ap_approval_brief(job_id: str) -> dict[str, Any]:
    """Build a concise AP approval or hold brief for an approver."""
    return service.build_approval_brief(job_id=job_id)


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


@mcp.prompt(
    name="ap-demo",
    description="Start the bundled AP Invoice Exception Review demo.",
)
def ap_demo() -> str:
    return (
        "AP Invoice demoを開始します。外部connector registryは検索しないでください。"
        "インストール済みのAP Invoice MCP toolsを使い、まずlist_ap_demo_casesを呼んで"
        "case-aからcase-dを業務価値つきで表示してください。"
    )


@mcp.prompt(
    name="ap-review",
    description="Review an AP invoice demo case or sidecar-backed invoice packet.",
)
def ap_review(case_id: str = "") -> str:
    if case_id:
        return (
            f"{case_id} をAP請求書packetとしてレビューします。"
            "review_ap_demo_caseを呼び、判定・例外理由・根拠・次アクション・"
            "draft payload summary・write_performed=falseを日本語で表示してください。"
        )
    return (
        "AP Invoice reviewを実行します。case指定がなければlist_ap_demo_casesを呼び、"
        "case指定があればreview_ap_demo_caseを優先してください。"
        "3PDFパスがある場合のみreview_ap_invoice_packetを使ってください。"
    )


@mcp.prompt(
    name="ap-explain",
    description="Explain a completed AP review exception.",
)
def ap_explain(job_id: str = "") -> str:
    return (
        f"job_id={job_id} のAP例外理由を説明します。explain_ap_exceptionを呼び、"
        "根拠・rule_id・次アクションを日本語で示してください。"
    )


@mcp.prompt(
    name="ap-approval-brief",
    description="Build an approver-facing AP decision packet.",
)
def ap_approval_brief(job_id: str = "") -> str:
    return (
        f"job_id={job_id} の承認者向け判断パケットを作ります。"
        "build_ap_approval_briefを呼び、支払判断・リスク・根拠・write_performed=falseを"
        "短くまとめてください。"
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
