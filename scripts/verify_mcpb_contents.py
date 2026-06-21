from __future__ import annotations

import json
import sys
import tempfile
import zipfile
from pathlib import Path

import fitz


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
    "ap_invoice_build_resolution_pack",
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
        if _version_tuple(version) < (0, 7, 0):
            failures.append(f"manifest version must be >= 0.7.0, got {version}")
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
                path = f"samples/{case_id}/{doc}.pdf"
                if path not in names:
                    failures.append(f"sample PDF missing: {path}")
        forbidden_json = [
            name
            for name in names
            if (
                name.startswith("samples/")
                or name.startswith("workflow-packs/ap-invoice-v1/samples/")
            )
            and name.endswith(".json")
        ]
        if forbidden_json:
            failures.append(f"sample JSON sidecars forbidden: {', '.join(sorted(forbidden_json)[:5])}")
        failures.extend(_check_rendered_pdfs(zf, names))
        if "workflow-packs/ap-invoice-v1/ruleset.yaml" not in names:
            failures.append("workflow ruleset missing")
        if ".claude-plugin/plugin.json" not in names:
            failures.append("root Claude plugin metadata missing")
        if "skills/ap-review/SKILL.md" not in names:
            failures.append("root AP review skill missing")
    if failures:
        for failure in failures:
            print(failure)
        raise SystemExit(1)
    print(f"MCPB content check passed: {bundle}")


def _check_rendered_pdfs(zf: zipfile.ZipFile, names: set[str]) -> list[str]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for case_id in REQUIRED_CASES:
            for doc in REQUIRED_DOCS:
                name = f"samples/{case_id}/{doc}.pdf"
                if name not in names:
                    continue
                pdf_path = tmp_dir / f"{case_id}-{doc}.pdf"
                pdf_path.write_bytes(zf.read(name))
                document = None
                try:
                    document = fitz.open(pdf_path)
                    page = document.load_page(0)
                    pixmap = page.get_pixmap(matrix=fitz.Matrix(0.25, 0.25), alpha=False)
                    if len(set(pixmap.samples)) < 8:
                        failures.append(f"rendered PDF appears blank: {name}")
                    text = page.get_text().strip()
                    if text:
                        failures.append(f"sample PDF must be image-rendered without text layer: {name}")
                except Exception as exc:
                    failures.append(f"sample PDF render failed: {name}: {exc}")
                finally:
                    if document is not None:
                        document.close()
    return failures


def _version_tuple(version: str) -> tuple[int, int, int]:
    parts = [int(part) for part in version.split(".")[:3]]
    while len(parts) < 3:
        parts.append(0)
    return (parts[0], parts[1], parts[2])


if __name__ == "__main__":
    main()
