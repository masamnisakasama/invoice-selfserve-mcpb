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


def test_skill_contains_v2_ux_guardrails() -> None:
    skill = SKILL_PATH.read_text("utf-8")

    assert "Do not search external connector registry" in skill
    assert "Do not search Airtable" in skill
    assert "Do not use Google Drive unless the user explicitly asks for Google Drive" in skill
    assert "If the user gives a folder path, call `ap_invoice_review_folder`" in skill
    assert "Show visible local PDF paths before review" in skill
    assert "Prefer high-level tools" in skill
    for slash in ("/ap-review", "/ap-demo", "/ap-explain", "/ap-approval-brief"):
        assert slash in skill
    assert "Always show `write_performed=false`" in skill
    assert "Use the installed AP Invoice Exception Review MCP tools" in skill


def test_manifest_lists_high_level_tools_before_low_level_tools() -> None:
    manifest = json.loads((PROJECT_ROOT / "manifest.json").read_text("utf-8"))
    tools = [tool["name"] for tool in manifest["tools"]]

    assert tools[:7] == [
        "ap_invoice_setup_demo_workspace",
        "ap_invoice_list_demo_cases",
        "ap_invoice_preview_folder",
        "ap_invoice_review_folder",
        "ap_invoice_review_demo_case",
        "ap_invoice_explain_exception",
        "ap_invoice_build_approval_brief",
    ]
    assert tools.index("ap_invoice_review_folder") < tools.index("create_ap_review_case")


def test_high_level_tool_descriptions_are_ux_focused() -> None:
    manifest = json.loads((PROJECT_ROOT / "manifest.json").read_text("utf-8"))
    descriptions = {tool["name"]: tool["description"] for tool in manifest["tools"]}

    assert "visible local" in descriptions["ap_invoice_setup_demo_workspace"]
    assert "visible local" in descriptions["ap_invoice_list_demo_cases"]
    assert "local folder" in descriptions["ap_invoice_preview_folder"]
    assert "visible local" in descriptions["ap_invoice_review_folder"]
    assert descriptions["create_ap_review_case"].startswith("Advanced:")
