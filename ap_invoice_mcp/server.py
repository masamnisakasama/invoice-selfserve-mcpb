from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, ImageContent, TextContent

from ap_invoice_core.engine import RULESET_VERSION, WORKFLOW_PACK
from ap_invoice_core.service import ReviewService


def _default_project_root() -> Path:
    source_root = Path(__file__).resolve().parents[1]
    if (source_root / "workflow-packs" / WORKFLOW_PACK).is_dir():
        return source_root
    return Path.cwd()


service = ReviewService(project_root=_default_project_root())
mcp = FastMCP("AP Invoice Exception Review MCPB")


def _pre_go_tool_blocked(tool_name: str) -> dict[str, Any]:
    return {
        "status": "blocked",
        "error_code": "CLAUDE_OCR_SMOKE_GO_REQUIRED",
        "tool_name": tool_name,
        "message_ja": (
            "このClaude OCR版MCPBはMilestone 0のGo/No-Go確認段階です。"
            "旧sidecar JSONベースのAPレビューを実行するとOCRデモとして誤認されるため、"
            "レビュー系toolは実機Go確認とno-sidecar実装が完了するまで停止しています。"
        ),
        "next_action_ja": (
            "ap_invoice_ocr_smoke_testを実行し、Claudeが返却画像をOCRして"
            "ap_invoice_submit_ocr_smoke_test_resultへsubmitできるか確認してください。"
        ),
        "allowed_tools_now": [
            "ap_invoice_ocr_smoke_test",
            "ap_invoice_submit_ocr_smoke_test_result",
        ],
        "write_performed": False,
    }


@mcp.tool()
def ap_invoice_ocr_smoke_test() -> CallToolResult:
    """Return a fixed invoice image as MCP image content for Claude OCR Go/No-Go."""
    result = service.create_ocr_smoke_test()
    return CallToolResult(
        content=[
            TextContent(type="text", text=str(result["instruction_text"])),
            ImageContent(
                type="image",
                data=str(result["image_base64"]),
                mimeType=str(result["image_mime_type"]),
            ),
        ],
        structuredContent=result["structured_content"],
        isError=False,
    )


@mcp.tool()
def ap_invoice_submit_ocr_smoke_test_result(
    run_id: str,
    ocr_result: dict[str, Any],
) -> dict[str, Any]:
    """Validate and save Claude's OCR result for the fixed smoke-test invoice image."""
    return service.submit_ocr_smoke_test_result(run_id=run_id, ocr_result=ocr_result)


@mcp.tool()
def ap_invoice_setup_demo_workspace(
    workspace_dir: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Export bundled demo PDFs to a visible local APInvoiceDemo workspace."""
    return _pre_go_tool_blocked("ap_invoice_setup_demo_workspace")


@mcp.tool()
def ap_invoice_list_demo_cases() -> dict[str, Any]:
    """List visible local AP invoice demo cases and expected outcomes."""
    return _pre_go_tool_blocked("ap_invoice_list_demo_cases")


@mcp.tool()
def ap_invoice_preview_folder(folder_path: str) -> dict[str, Any]:
    """Preview and classify invoice, PO, and goods receipt PDFs in a local folder."""
    return _pre_go_tool_blocked("ap_invoice_preview_folder")


@mcp.tool()
def ap_invoice_review_folder(
    folder_path: str,
    tenant_id: str = "demo-tenant",
    target_system: str = "generic_ap",
) -> dict[str, Any]:
    """Review a visible local folder containing invoice, PO, and goods receipt PDFs."""
    return _pre_go_tool_blocked("ap_invoice_review_folder")


@mcp.tool()
def ap_invoice_review_demo_case(
    case_id: str,
    tenant_id: str = "demo-tenant",
    target_system: str = "generic_ap",
) -> dict[str, Any]:
    """Review a bundled demo case from the visible APInvoiceDemo workspace."""
    return _pre_go_tool_blocked("ap_invoice_review_demo_case")


@mcp.tool()
def ap_invoice_explain_exception(job_id: str, audience: str = "ap_operator") -> dict[str, Any]:
    """Explain AP invoice review exceptions with evidence, rule IDs, and next actions."""
    return _pre_go_tool_blocked("ap_invoice_explain_exception")


@mcp.tool()
def ap_invoice_build_approval_brief(job_id: str) -> dict[str, Any]:
    """Build a concise AP invoice approval or hold brief for an approver."""
    return _pre_go_tool_blocked("ap_invoice_build_approval_brief")


@mcp.tool()
def list_ap_demo_cases() -> dict[str, Any]:
    """List bundled AP invoice demo cases and explain their business value."""
    return _pre_go_tool_blocked("list_ap_demo_cases")


@mcp.tool()
def review_ap_demo_case(
    case_id: str,
    tenant_id: str = "demo-tenant",
    target_system: str = "generic_ap",
) -> dict[str, Any]:
    """Run a bundled AP invoice demo case end-to-end and return a decision packet."""
    return _pre_go_tool_blocked("review_ap_demo_case")


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
    return _pre_go_tool_blocked("review_ap_invoice_packet")


@mcp.tool()
def explain_ap_exception(job_id: str, audience: str = "ap_operator") -> dict[str, Any]:
    """Explain AP review exceptions with evidence, rule IDs, and next actions."""
    return _pre_go_tool_blocked("explain_ap_exception")


@mcp.tool()
def build_ap_approval_brief(job_id: str) -> dict[str, Any]:
    """Build a concise AP approval or hold brief for an approver."""
    return _pre_go_tool_blocked("build_ap_approval_brief")


@mcp.tool()
def create_ap_review_case(
    tenant_id: str,
    workflow_pack: str = WORKFLOW_PACK,
    ruleset_version: str = RULESET_VERSION,
    case_label: str = "",
) -> dict[str, Any]:
    """Create an AP invoice review case and return required upload slots."""
    return _pre_go_tool_blocked("create_ap_review_case")


@mcp.tool()
def upload_ap_document(case_id: str, document_type: str, file_path: str) -> dict[str, Any]:
    """Attach a local invoice, purchase order, or goods receipt PDF to a case."""
    return _pre_go_tool_blocked("upload_ap_document")


@mcp.tool()
def start_ap_invoice_review(case_id: str) -> dict[str, Any]:
    """Run deterministic AP 3-way match, duplicate, vendor, and tax checks."""
    return _pre_go_tool_blocked("start_ap_invoice_review")


@mcp.tool()
def get_ap_invoice_review_result(job_id: str) -> dict[str, Any]:
    """Return a completed AP review decision packet with evidence and artifacts."""
    return _pre_go_tool_blocked("get_ap_invoice_review_result")


@mcp.tool()
def build_erp_draft_payload(
    case_id: str,
    target_system: str,
    mode: str = "draft_only",
) -> dict[str, Any]:
    """Build a draft-only ERP/SaaS payload. External writes are never performed."""
    return _pre_go_tool_blocked("build_erp_draft_payload")


@mcp.prompt(
    name="ap-demo",
    description="Start the bundled AP Invoice Exception Review demo.",
)
def ap_demo() -> str:
    return (
        "AP Invoice demoを開始します。vNextのClaude OCR版では、まず"
        "ap_invoice_ocr_smoke_testを呼び、返された画像をClaude vision/OCRで読み、"
        "ap_invoice_submit_ocr_smoke_test_resultへinvoice_numberとtotal_amountを"
        "submitしてください。OCR_SMOKE_TEST_PASSEDが出たらMilestone 0通過として"
        "ユーザーへ報告し、APレビュー本体はno-sidecar実装が入るまで進めないでください。"
        "Airtable、Google Drive、外部connector registryは検索しないでください。"
    )


@mcp.prompt(
    name="ap-review",
    description="Review an AP invoice demo case or sidecar-backed invoice packet.",
)
def ap_review(case_id: str = "") -> str:
    if case_id:
        return (
            f"{case_id} をAP請求書packetとしてレビューします。"
            "このClaude OCR版では旧sidecarレビューは禁止です。まず"
            "ap_invoice_ocr_smoke_testを実行し、返却画像をOCRして"
            "ap_invoice_submit_ocr_smoke_test_resultへsubmitしてください。"
            "OCR_SMOKE_TEST_PASSED後も、no-sidecar本実装が入るまでは"
            "APレビュー本体へ進めないでください。"
        )
    return (
        "AP Invoice reviewを実行します。このClaude OCR版では旧sidecarレビューは禁止です。"
        "まずap_invoice_ocr_smoke_testを呼び、返された画像をOCRして"
        "ap_invoice_submit_ocr_smoke_test_resultへsubmitしてください。"
        "OCR_SMOKE_TEST_PASSED後も、no-sidecar本実装が入るまではAPレビュー本体へ"
        "進めないでください。Airtableや外部registryは検索しないでください。"
    )


@mcp.prompt(
    name="ap-explain",
    description="Explain a completed AP review exception.",
)
def ap_explain(job_id: str = "") -> str:
    return (
        f"job_id={job_id} のAP例外理由を説明します。ap_invoice_explain_exceptionを呼び、"
        "根拠・rule_id・次アクションを日本語で示してください。"
    )


@mcp.prompt(
    name="ap-approval-brief",
    description="Build an approver-facing AP decision packet.",
)
def ap_approval_brief(job_id: str = "") -> str:
    return (
        f"job_id={job_id} の承認者向け判断パケットを作ります。"
        "ap_invoice_build_approval_briefを呼び、支払判断・リスク・根拠・"
        "write_performed=falseを短くまとめてください。"
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
