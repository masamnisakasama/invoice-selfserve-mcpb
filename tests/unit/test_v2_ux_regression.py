from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKILL_PATH = (
    PROJECT_ROOT
    / "enterprise-bundle"
    / "plugin"
    / "ap-invoice-review"
    / "skills"
    / "ap-review"
    / "SKILL.md"
)
WORKFLOW_SKILL_PATH = PROJECT_ROOT / "workflow-packs" / "ap-invoice-v1" / "SKILL.md"
SLASH_COMMAND_PATH = PROJECT_ROOT / "commands" / "ap-review.md"


def test_skill_contains_v2_ux_guardrails() -> None:
    skill = SKILL_PATH.read_text("utf-8")

    assert "Do not search external connector registry" in skill
    assert "Do not search Airtable" in skill
    assert "Do not use Google Drive unless the user explicitly asks for Google Drive" in skill
    assert "ap_invoice_prepare_ocr_run" in skill
    assert "ap_invoice_submit_ocr_result" in skill
    assert "ap_invoice_review_from_ocr_result" in skill
    assert "ap_invoice_build_resolution_pack" in skill
    assert "Do not read JSON sidecars" in skill
    assert "Do not skip OCR" in skill
    assert "Prefer high-level tools" in skill
    for slash in ("/ap-review", "/ap-demo", "/ap-explain", "/ap-approval-brief"):
        assert slash in skill
    assert "Always show `write_performed=false`" in skill
    assert "Use the installed AP Invoice Exception Review MCP tools" in skill


def test_workflow_skill_contains_desktop_auto_flow_guardrails() -> None:
    skill = WORKFLOW_SKILL_PATH.read_text("utf-8")

    assert "ap_invoice_build_resolution_pack" in skill
    assert "Resolution Pack" in skill
    assert "write_performed=false" in skill
    assert "請求書のみ | このデモMCPBではレビューを開始しない" in skill
    assert "PO/GRNなしでも動く" not in skill
    assert "available checks" not in skill


def test_ap_review_slash_command_enforces_deterministic_ocr_flow() -> None:
    command = SLASH_COMMAND_PATH.read_text("utf-8")

    assert command.startswith("---\ndescription: ")
    assert "/ap-review — AP Invoice Review" in command
    assert "確認・質問は一切しない" in command
    assert "case-a → case-a-pay-ready" in command
    assert "case-f → case-f-tax-review" in command
    assert "ap_invoice_setup_demo_workspace()" in command
    assert "ap_invoice_review_demo_case(case_id)" in command
    assert "ap_invoice_prepare_ocr_run(folder_path)" in command
    assert "ap_invoice_submit_ocr_result(run_id, ocr_results)" in command
    assert "ap_invoice_review_from_ocr_result(run_id)" in command
    assert "write_performed=false" in command
    assert "レガシーツール（list_ap_demo_cases, review_ap_demo_case 等）の使用" in command
    assert "フォールバックや代替フロー" in command
    assert "ERP/SaaS への書き込みが行われたと示唆すること" in command


def test_manifest_lists_high_level_tools_before_low_level_tools() -> None:
    manifest = json.loads((PROJECT_ROOT / "manifest.json").read_text("utf-8"))
    tools = [tool["name"] for tool in manifest["tools"]]

    assert tools[:10] == [
        "ap_invoice_setup_demo_workspace",
        "ap_invoice_list_demo_cases",
        "ap_invoice_prepare_ocr_run",
        "ap_invoice_submit_ocr_result",
        "ap_invoice_review_from_ocr_result",
        "ap_invoice_preview_folder",
        "ap_invoice_review_folder",
        "ap_invoice_review_demo_case",
        "ap_invoice_explain_exception",
        "ap_invoice_build_approval_brief",
    ]
    assert tools.index("ap_invoice_review_folder") < tools.index("create_ap_review_case")
    assert tools.index("ap_invoice_build_resolution_pack") < tools.index("create_ap_review_case")


def test_high_level_tool_descriptions_are_ux_focused() -> None:
    manifest = json.loads((PROJECT_ROOT / "manifest.json").read_text("utf-8"))
    descriptions = {tool["name"]: tool["description"] for tool in manifest["tools"]}

    assert "image-rendered demo PDFs" in descriptions["ap_invoice_setup_demo_workspace"]
    assert "visible local" in descriptions["ap_invoice_list_demo_cases"]
    assert "Claude OCR" in descriptions["ap_invoice_review_folder"]
    assert "_runs" in descriptions["ap_invoice_submit_ocr_result"]
    assert "next-action messages" in descriptions["ap_invoice_build_resolution_pack"]
