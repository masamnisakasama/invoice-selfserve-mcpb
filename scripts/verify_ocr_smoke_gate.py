from __future__ import annotations

import asyncio
import base64
import json
import sys
import zipfile
from pathlib import Path
from typing import Any, cast

from mcp.types import CallToolResult, ImageContent, TextContent

from ap_invoice_mcp.server import mcp


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_MANIFEST_NAME = "ap-invoice-review-claude-ocr"
EXPECTED_DISPLAY_NAME = "AP Invoice Review — Claude OCR"
EXPECTED_NEXT_TOOL = "ap_invoice_submit_ocr_smoke_test_result"
FORBIDDEN_ANSWER_TOKENS = ("INV-SMOKE-0001", "110000", "110,000")


def main() -> None:
    bundle = Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT_ROOT / "dist/ap-invoice-review.mcpb"
    failures: list[str] = []
    failures.extend(_check_bundle_manifest(bundle))
    failures.extend(asyncio.run(_check_live_tool_result()))

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        raise SystemExit(1)

    print("OCR smoke gate local checks passed.")
    print("Manual Go/No-Go still required: run the MCPB in real Claude Desktop and confirm Claude OCRs the returned image, then calls the submit tool.")


def _check_bundle_manifest(bundle: Path) -> list[str]:
    failures: list[str] = []
    if not bundle.is_file():
        return [f"bundle not found: {bundle}"]
    with zipfile.ZipFile(bundle) as zf:
        names = set(zf.namelist())
        if "manifest.json" not in names:
            return ["manifest.json missing from bundle"]
        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
    if manifest.get("name") != EXPECTED_MANIFEST_NAME:
        failures.append(f"manifest name must be {EXPECTED_MANIFEST_NAME}")
    if manifest.get("display_name") != EXPECTED_DISPLAY_NAME:
        failures.append(f"manifest display_name must be {EXPECTED_DISPLAY_NAME}")
    tools = [tool.get("name") for tool in manifest.get("tools", [])]
    for required in ("ap_invoice_ocr_smoke_test", EXPECTED_NEXT_TOOL):
        if required not in tools:
            failures.append(f"manifest tool missing: {required}")
    return failures


async def _check_live_tool_result() -> list[str]:
    failures: list[str] = []
    result = cast(CallToolResult, await mcp.call_tool("ap_invoice_ocr_smoke_test", {}))
    if result.isError:
        failures.append("ap_invoice_ocr_smoke_test returned isError=true")
    if not result.structuredContent:
        failures.append("ap_invoice_ocr_smoke_test missing structuredContent")
        structured = {}
    else:
        structured = result.structuredContent
    if not str(structured.get("run_id", "")).startswith("ocr-smoke-"):
        failures.append("structuredContent.run_id must start with ocr-smoke-")
    if structured.get("expected_fields") != ["invoice_number", "total_amount"]:
        failures.append("structuredContent.expected_fields must only name required OCR fields")
    if structured.get("next_tool") != EXPECTED_NEXT_TOOL:
        failures.append(f"structuredContent.next_tool must be {EXPECTED_NEXT_TOOL}")

    content_types = [content.type for content in result.content]
    if content_types != ["text", "image"]:
        failures.append(f"tool content must be [text, image], got {content_types}")
        return failures

    text = result.content[0]
    image = result.content[1]
    if not isinstance(text, TextContent):
        failures.append("first content item must be TextContent")
    if not isinstance(image, ImageContent):
        failures.append("second content item must be ImageContent")
        return failures
    if image.mimeType != "image/png":
        failures.append("image content mimeType must be image/png")
    try:
        png = base64.b64decode(image.data, validate=True)
    except ValueError:
        failures.append("image content data must be valid base64")
        return failures
    if not png.startswith(b"\x89PNG\r\n\x1a\n"):
        failures.append("image content data must decode to PNG bytes")
    if len(png) < 10_000:
        failures.append("smoke image PNG is unexpectedly small")

    text_payload = text.text if isinstance(text, TextContent) else ""
    structured_payload = json.dumps(structured, ensure_ascii=False)
    for token in FORBIDDEN_ANSWER_TOKENS:
        if token in text_payload:
            failures.append(f"answer token leaked in tool text: {token}")
        if token in structured_payload:
            failures.append(f"answer token leaked in structuredContent: {token}")
    failures.extend(await _check_legacy_tools_are_blocked())
    return failures


async def _check_legacy_tools_are_blocked() -> list[str]:
    failures: list[str] = []
    legacy_calls = {
        "review_ap_invoice_packet": {
            "tenant_id": "demo-tenant",
            "invoice_path": "samples/case-a-pay-ready/invoice.pdf",
            "purchase_order_path": "samples/case-a-pay-ready/purchase_order.pdf",
            "goods_receipt_path": "samples/case-a-pay-ready/goods_receipt.pdf",
        },
    }
    for tool_name, arguments in legacy_calls.items():
        result = await mcp.call_tool(tool_name, arguments)
        payload = _tool_payload(result)
        if payload.get("status") != "blocked":
            failures.append(f"{tool_name} must be blocked in the Claude OCR package")
        if payload.get("error_code") != "LEGACY_SIDECAR_FLOW_DISABLED":
            failures.append(f"{tool_name} must return LEGACY_SIDECAR_FLOW_DISABLED")
    return failures


def _tool_payload(result: object) -> dict[str, Any]:
    if isinstance(result, CallToolResult):
        return _first_text_json_payload(result)
    if isinstance(result, tuple) and len(result) >= 2 and isinstance(result[1], dict):
        return result[1]
    return {}


def _first_text_json_payload(result: CallToolResult) -> dict[str, Any]:
    if not result.content or not isinstance(result.content[0], TextContent):
        return {}
    try:
        payload = json.loads(result.content[0].text)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


if __name__ == "__main__":
    main()
