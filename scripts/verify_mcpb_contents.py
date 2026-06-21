from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path


REQUIRED_CASES = (
    "case-a-pay-ready",
    "case-b-po-mismatch",
    "case-c-duplicate",
    "case-d-vendor-review",
    "case-e-grn-mismatch",
    "case-f-tax-review",
)
REQUIRED_DOCS = ("invoice", "purchase_order", "goods_receipt")
REQUIRED_TOOLS = (
    "ap_invoice_ocr_smoke_test",
    "ap_invoice_submit_ocr_smoke_test_result",
    "ap_invoice_setup_demo_workspace",
    "ap_invoice_list_demo_cases",
    "ap_invoice_preview_folder",
    "ap_invoice_review_folder",
    "ap_invoice_review_demo_case",
    "ap_invoice_explain_exception",
    "ap_invoice_build_approval_brief",
)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_mcpb_contents.py dist/ap-invoice-review.mcpb")
    bundle = Path(sys.argv[1])
    if not bundle.is_file():
        raise SystemExit(f"bundle not found: {bundle}")
    failures: list[str] = []
    with zipfile.ZipFile(bundle) as zf:
        names = set(zf.namelist())
        if "manifest.json" not in names:
            failures.append("manifest.json missing")
            manifest = {}
        else:
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        version = str(manifest.get("version", "0"))
        if _version_tuple(version) < (0, 6, 0):
            failures.append(f"manifest version must be >= 0.6.0, got {version}")
        if manifest.get("name") != "ap-invoice-review-claude-ocr":
            failures.append("manifest name must be ap-invoice-review-claude-ocr")
        if "Claude OCR" not in str(manifest.get("display_name", "")):
            failures.append("manifest display_name must mention Claude OCR")
        tools = [tool.get("name") for tool in manifest.get("tools", [])]
        for required_tool in REQUIRED_TOOLS:
            if required_tool not in tools:
                failures.append(f"manifest tool missing: {required_tool}")
        for case_id in REQUIRED_CASES:
            for doc in REQUIRED_DOCS:
                for suffix in (".pdf", ".json"):
                    path = f"samples/{case_id}/{doc}{suffix}"
                    if path not in names:
                        failures.append(f"sample artifact missing: {path}")
        if "workflow-packs/ap-invoice-v1/ruleset.yaml" not in names:
            failures.append("workflow ruleset missing")
    if failures:
        for failure in failures:
            print(failure)
        raise SystemExit(1)
    print(f"MCPB content check passed: {bundle}")


def _version_tuple(version: str) -> tuple[int, int, int]:
    parts = [int(part) for part in version.split(".")[:3]]
    while len(parts) < 3:
        parts.append(0)
    return (parts[0], parts[1], parts[2])


if __name__ == "__main__":
    main()
