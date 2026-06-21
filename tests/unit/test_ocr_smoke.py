from __future__ import annotations

import asyncio
import base64
import json
from pathlib import Path

from mcp.types import ImageContent, TextContent

from ap_invoice_core.ocr_smoke import create_smoke_invoice_png
from ap_invoice_core.service import ReviewService
from ap_invoice_mcp.server import (
    ap_invoice_review_demo_case,
    ap_invoice_setup_demo_workspace,
    mcp,
    review_ap_invoice_packet,
)
from tests.helpers import PROJECT_ROOT


def test_ocr_smoke_png_is_nonblank() -> None:
    png = create_smoke_invoice_png()

    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(png) > 10_000


def test_ocr_smoke_service_does_not_return_expected_answer_json(tmp_path: Path) -> None:
    service = ReviewService(
        project_root=PROJECT_ROOT,
        artifact_root=tmp_path / "artifacts",
        default_workspace_dir=tmp_path / "APInvoiceDemo",
    )

    result = service.create_ocr_smoke_test()

    assert result["structured_content"]["expected_fields"] == ["invoice_number", "total_amount"]
    assert result["structured_content"]["next_tool"] == "ap_invoice_submit_ocr_smoke_test_result"
    assert "INV-SMOKE-0001" not in result["instruction_text"]
    assert "110000" not in json.dumps(result["structured_content"])


def test_submit_ocr_smoke_result_passes_exact_values_and_saves(tmp_path: Path) -> None:
    service = ReviewService(
        project_root=PROJECT_ROOT,
        artifact_root=tmp_path / "artifacts",
        default_workspace_dir=tmp_path / "APInvoiceDemo",
    )
    smoke = service.create_ocr_smoke_test()

    result = service.submit_ocr_smoke_test_result(
        run_id=str(smoke["run_id"]),
        ocr_result={"invoice_number": "INV-SMOKE-0001", "total_amount": "JPY 110,000"},
    )

    assert result["status"] == "OCR_SMOKE_TEST_PASSED"
    output_path = Path(result["ocr_result_path"])
    assert output_path.is_file()
    assert output_path.parent == tmp_path / "APInvoiceDemo" / "_runs" / smoke["run_id"] / "ocr_results"
    saved = json.loads(output_path.read_text("utf-8"))
    assert saved["ocr_result"]["invoice_number"] == "INV-SMOKE-0001"
    assert saved["ocr_result"]["total_amount"] == 110000
    assert saved["write_performed"] is False


def test_submit_ocr_smoke_result_fails_wrong_values(tmp_path: Path) -> None:
    service = ReviewService(
        project_root=PROJECT_ROOT,
        artifact_root=tmp_path / "artifacts",
        default_workspace_dir=tmp_path / "APInvoiceDemo",
    )
    smoke = service.create_ocr_smoke_test()

    result = service.submit_ocr_smoke_test_result(
        run_id=str(smoke["run_id"]),
        ocr_result={"invoice_number": "INV-SMOKE-9999", "total_amount": 1},
    )

    assert result["status"] == "OCR_SMOKE_TEST_FAILED"
    assert result["validation_errors"]
    assert Path(result["ocr_result_path"]).is_file()


def test_ocr_smoke_tool_returns_image_content() -> None:
    result = asyncio.run(mcp.call_tool("ap_invoice_ocr_smoke_test", {}))

    assert result.structuredContent
    assert result.structuredContent["run_id"].startswith("ocr-smoke-")
    assert result.structuredContent["expected_fields"] == ["invoice_number", "total_amount"]
    assert result.structuredContent["next_tool"] == "ap_invoice_submit_ocr_smoke_test_result"
    assert [content.type for content in result.content] == ["text", "image"]

    text = result.content[0]
    image = result.content[1]
    assert isinstance(text, TextContent)
    assert isinstance(image, ImageContent)
    assert "INV-SMOKE-0001" not in text.text
    assert image.mimeType == "image/png"
    assert base64.b64decode(image.data).startswith(b"\x89PNG\r\n\x1a\n")


def test_claude_ocr_gate_blocks_legacy_sidecar_tools() -> None:
    setup = ap_invoice_setup_demo_workspace()
    demo_review = ap_invoice_review_demo_case(case_id="case-a")
    packet_review = review_ap_invoice_packet(
        tenant_id="demo-tenant",
        invoice_path="samples/case-a-pay-ready/invoice.pdf",
        purchase_order_path="samples/case-a-pay-ready/purchase_order.pdf",
        goods_receipt_path="samples/case-a-pay-ready/goods_receipt.pdf",
    )

    for result in (setup, demo_review, packet_review):
        assert result["status"] == "blocked"
        assert result["error_code"] == "CLAUDE_OCR_SMOKE_GO_REQUIRED"
        assert result["allowed_tools_now"] == [
            "ap_invoice_ocr_smoke_test",
            "ap_invoice_submit_ocr_smoke_test_result",
        ]
        assert result["write_performed"] is False
