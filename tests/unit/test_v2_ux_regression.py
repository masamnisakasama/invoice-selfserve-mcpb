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
    assert "Prefer high-level tools" in skill
    for slash in ("/ap-review", "/ap-demo", "/ap-explain", "/ap-approval-brief"):
        assert slash in skill
    assert "Always show `write_performed=false`" in skill
    assert "Use the installed AP Invoice Exception Review MCP tools" in skill


def test_manifest_lists_high_level_tools_before_low_level_tools() -> None:
    manifest = json.loads((PROJECT_ROOT / "manifest.json").read_text("utf-8"))
    tools = [tool["name"] for tool in manifest["tools"]]

    assert tools[:5] == [
        "list_ap_demo_cases",
        "review_ap_demo_case",
        "review_ap_invoice_packet",
        "explain_ap_exception",
        "build_ap_approval_brief",
    ]
    assert tools.index("review_ap_demo_case") < tools.index("create_ap_review_case")


def test_high_level_tool_descriptions_are_ux_focused() -> None:
    manifest = json.loads((PROJECT_ROOT / "manifest.json").read_text("utf-8"))
    descriptions = {tool["name"]: tool["description"] for tool in manifest["tools"]}

    assert "bundled" in descriptions["list_ap_demo_cases"]
    assert "end-to-end" in descriptions["review_ap_demo_case"]
    assert "end-to-end" in descriptions["review_ap_invoice_packet"]
    assert descriptions["create_ap_review_case"].startswith("Advanced:")
