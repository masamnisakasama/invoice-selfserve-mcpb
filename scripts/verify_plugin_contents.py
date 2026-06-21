from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path


REQUIRED_FILES = (
    ".claude-plugin/plugin.json",
    ".mcp.json",
    "skills/ap-review/SKILL.md",
    "workflow-packs/ap-invoice-v1/SKILL.md",
    "ap_invoice_core/resolution.py",
    "ap_invoice_mcp/server.py",
    "samples/case-a-pay-ready/invoice.pdf",
)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_plugin_contents.py dist/ap-invoice-review.plugin")
    plugin = Path(sys.argv[1])
    if not plugin.is_file():
        raise SystemExit(f"plugin not found: {plugin}")
    failures: list[str] = []
    with zipfile.ZipFile(plugin) as zf:
        names = set(zf.namelist())
        for required in REQUIRED_FILES:
            if required not in names:
                failures.append(f"plugin file missing: {required}")
        if ".claude-plugin/plugin.json" in names:
            plugin_json = json.loads(zf.read(".claude-plugin/plugin.json").decode("utf-8-sig"))
            if plugin_json.get("name") != "ap-invoice-review":
                failures.append("plugin name must be ap-invoice-review")
        if "skills/ap-review/SKILL.md" in names:
            skill = zf.read("skills/ap-review/SKILL.md").decode("utf-8")
            if "Resolution Pack" not in skill:
                failures.append("plugin skill must mention Resolution Pack")
        if "ap_invoice_mcp/server.py" in names:
            server = zf.read("ap_invoice_mcp/server.py").decode("utf-8")
            if "ap_invoice_build_resolution_pack" not in server:
                failures.append("plugin MCP server must expose ap_invoice_build_resolution_pack")
        if any("\\" in name for name in names):
            failures.append("plugin zip entries must use forward slash paths")
    if failures:
        for failure in failures:
            print(failure)
        raise SystemExit(1)
    print(f"Plugin content check passed: {plugin}")


if __name__ == "__main__":
    main()
