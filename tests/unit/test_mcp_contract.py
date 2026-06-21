from __future__ import annotations

import asyncio
import json
from pathlib import Path

from mcp.types import CallToolResult

import ap_invoice_mcp.server as server
from ap_invoice_core.service import ReviewService
from ap_invoice_mcp.server import mcp
from tests.helpers import PROJECT_ROOT, ensure_samples


def test_mcp_tools_list_is_stable_and_schema_backed() -> None:
    tools = asyncio.run(mcp.list_tools())
    by_name = {tool.name: tool for tool in tools}
    assert sorted(by_name) == [
        "ap_invoice_build_approval_brief",
        "ap_invoice_build_resolution_pack",
        "ap_invoice_explain_exception",
        "ap_invoice_list_demo_cases",
        "ap_invoice_ocr_smoke_test",
        "ap_invoice_prepare_ocr_run",
        "ap_invoice_preview_folder",
        "ap_invoice_review_demo_case",
        "ap_invoice_review_folder",
        "ap_invoice_review_from_ocr_result",
        "ap_invoice_setup_demo_workspace",
        "ap_invoice_submit_ocr_result",
        "ap_invoice_submit_ocr_smoke_test_result",
        "build_ap_approval_brief",
        "build_erp_draft_payload",
        "create_ap_review_case",
        "explain_ap_exception",
        "get_ap_invoice_review_result",
        "list_ap_demo_cases",
        "review_ap_demo_case",
        "review_ap_invoice_packet",
        "start_ap_invoice_review",
        "upload_ap_document",
    ]
    for tool in tools:
        assert tool.inputSchema["type"] == "object"
        assert "properties" in tool.inputSchema

    assert by_name["ap_invoice_review_folder"].inputSchema["required"] == ["folder_path"]
    assert by_name["ap_invoice_prepare_ocr_run"].inputSchema["required"] == ["folder_path"]
    assert by_name["ap_invoice_submit_ocr_result"].inputSchema["required"] == [
        "run_id",
        "ocr_results",
    ]
    assert by_name["ap_invoice_review_from_ocr_result"].inputSchema["required"] == ["run_id"]
    assert by_name["ap_invoice_build_resolution_pack"].inputSchema["required"] == ["run_id"]
    assert by_name["ap_invoice_preview_folder"].inputSchema["required"] == ["folder_path"]
    assert by_name["ap_invoice_submit_ocr_smoke_test_result"].inputSchema["required"] == [
        "run_id",
        "ocr_result",
    ]
    assert by_name["review_ap_demo_case"].inputSchema["required"] == ["case_id"]
    assert by_name["review_ap_invoice_packet"].inputSchema["required"] == [
        "tenant_id",
        "invoice_path",
        "purchase_order_path",
        "goods_receipt_path",
    ]
    assert by_name["explain_ap_exception"].inputSchema["required"] == ["job_id"]
    assert by_name["build_ap_approval_brief"].inputSchema["required"] == ["job_id"]


def test_mcp_prompts_list_is_stable() -> None:
    prompts = asyncio.run(mcp.list_prompts())
    names = sorted(prompt.name for prompt in prompts)

    assert names == [
        "ap-approval-brief",
        "ap-demo",
        "ap-explain",
        "ap-resolution-pack",
        "ap-review",
    ]


def test_manifest_static_prompts_match_mcp_prompt_names() -> None:
    prompts = asyncio.run(mcp.list_prompts())
    manifest = json.loads((PROJECT_ROOT / "manifest.json").read_text("utf-8"))

    assert sorted(prompt["name"] for prompt in manifest["prompts"]) == sorted(
        prompt.name for prompt in prompts
    )


def test_prepare_ocr_run_tool_returns_image_content(tmp_path: Path) -> None:
    ensure_samples()
    original_service = server.service
    server.service = ReviewService(
        project_root=PROJECT_ROOT,
        artifact_root=tmp_path / "artifacts",
        default_workspace_dir=tmp_path / "APInvoiceDemo",
    )
    try:
        result = asyncio.run(
            mcp.call_tool(
                "ap_invoice_prepare_ocr_run",
                {"folder_path": str(PROJECT_ROOT / "samples" / "case-a-pay-ready")},
            )
        )
    finally:
        server.service = original_service

    assert isinstance(result, CallToolResult)
    assert result.structuredContent["status"] == "OCR_PREPARED"
    assert result.structuredContent["next_tool"] == "ap_invoice_submit_ocr_result"
    assert [part.type for part in result.content].count("image") == 3
    assert all(getattr(part, "mimeType", None) == "image/png" for part in result.content if part.type == "image")
