from __future__ import annotations

import asyncio

from ap_invoice_mcp.server import mcp


def test_mcp_tools_list_is_stable_and_schema_backed() -> None:
    tools = asyncio.run(mcp.list_tools())
    by_name = {tool.name: tool for tool in tools}
    assert sorted(by_name) == [
        "ap_invoice_build_approval_brief",
        "ap_invoice_explain_exception",
        "ap_invoice_list_demo_cases",
        "ap_invoice_ocr_smoke_test",
        "ap_invoice_preview_folder",
        "ap_invoice_review_demo_case",
        "ap_invoice_review_folder",
        "ap_invoice_setup_demo_workspace",
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
        "ap-review",
    ]
