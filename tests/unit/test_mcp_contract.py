from __future__ import annotations

import asyncio

from ap_invoice_mcp.server import mcp


def test_mcp_tools_list_is_stable_and_schema_backed() -> None:
    tools = asyncio.run(mcp.list_tools())
    by_name = {tool.name: tool for tool in tools}
    assert sorted(by_name) == [
        "build_erp_draft_payload",
        "create_ap_review_case",
        "get_ap_invoice_review_result",
        "start_ap_invoice_review",
        "upload_ap_document",
    ]
    for tool in tools:
        assert tool.inputSchema["type"] == "object"
        assert "properties" in tool.inputSchema
