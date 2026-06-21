from __future__ import annotations

import json
import math
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
MIN_VISUAL_RMS_DIFF = 18.0
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
REQUIRED_PROMPTS = (
    "ap-demo",
    "ap-review",
    "ap-explain",
    "ap-approval-brief",
    "ap-resolution-pack",
)
REQUIRED_COMMANDS = (
    "commands/ap-review.md",
    ".claude/commands/ap-review.md",
)
REQUIRED_SKILLS = (
    "skills/ap-review/SKILL.md",
    ".claude/skills/ap-review/SKILL.md",
)
COMMAND_MUST_CONTAIN = (
    "/ap-review — AP Invoice Review",
    "ap_invoice_setup_demo_workspace()",
    "ap_invoice_review_demo_case(case_id)",
    "ap_invoice_prepare_ocr_run(folder_path)",
    "ap_invoice_submit_ocr_result(run_id, ocr_results)",
    "ap_invoice_review_from_ocr_result(run_id)",
    "write_performed=false",
    "レガシーツール（list_ap_demo_cases, review_ap_demo_case 等）の使用",
    "フォールバックや代替フロー",
)
SKILL_MUST_CONTAIN = (
    "name: ap-review",
    "ap_invoice_review_demo_case",
    "ap_invoice_submit_ocr_result",
    "ap_invoice_review_from_ocr_result",
    "ap_invoice_build_resolution_pack",
    "write_performed=false",
)
TEXT_EXTENSIONS_NO_BOM = (".json", ".md", ".py", ".toml", ".yaml", ".yml")
BOM = b"\xef\xbb\xbf"
FORBIDDEN_WORK_NOTES = (
    "docs/HANDOFF_SESSION3.md",
    "docs/codex-task.md",
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
        failures.extend(_check_no_bom(zf, names))
        for forbidden_note in FORBIDDEN_WORK_NOTES:
            if forbidden_note in names:
                failures.append(f"work note must not be packaged: {forbidden_note}")
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
        prompts_by_name = {prompt.get("name"): prompt for prompt in manifest.get("prompts", [])}
        for required_prompt in REQUIRED_PROMPTS:
            if required_prompt not in prompts_by_name:
                failures.append(f"manifest prompt missing: {required_prompt}")
        ap_review_prompt = prompts_by_name.get("ap-review", {})
        if ap_review_prompt.get("arguments") != ["case_id"]:
            failures.append("manifest ap-review prompt must declare case_id argument")
        ap_review_prompt_text = str(ap_review_prompt.get("text", ""))
        for required_text in (
            "ap_invoice_review_demo_case",
            "ap_invoice_prepare_ocr_run",
            "ap_invoice_submit_ocr_result",
            "ap_invoice_review_from_ocr_result",
            "write_performed=false",
            "fallbackは禁止",
        ):
            if required_text not in ap_review_prompt_text:
                failures.append(f"manifest ap-review prompt missing guardrail: {required_text}")
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
        failures.extend(_check_document_visual_distinction(zf, names))
        if "workflow-packs/ap-invoice-v1/ruleset.yaml" not in names:
            failures.append("workflow ruleset missing")
        if ".claude-plugin/plugin.json" not in names:
            failures.append("root Claude plugin metadata missing")
        for skill_path in REQUIRED_SKILLS:
            if skill_path not in names:
                failures.append(f"AP review skill missing: {skill_path}")
                continue
            skill = zf.read(skill_path).decode("utf-8")
            for required_text in SKILL_MUST_CONTAIN:
                if required_text not in skill:
                    failures.append(f"{skill_path} missing required guardrail: {required_text}")
            if "PO/GRNなしでも動く" in skill:
                failures.append(f"{skill_path} must not allow PO/GRN-free fallback")
        for command_path in REQUIRED_COMMANDS:
            if command_path not in names:
                failures.append(f"slash command missing: {command_path}")
                continue
            command = zf.read(command_path).decode("utf-8")
            for required_text in COMMAND_MUST_CONTAIN:
                if required_text not in command:
                    failures.append(f"{command_path} missing required guardrail: {required_text}")
    if failures:
        for failure in failures:
            print(failure)
        raise SystemExit(1)
    print(f"MCPB content check passed: {bundle}")


def _check_no_bom(zf: zipfile.ZipFile, names: set[str]) -> list[str]:
    failures: list[str] = []
    for name in sorted(names):
        if name.endswith(TEXT_EXTENSIONS_NO_BOM) and zf.read(name).startswith(BOM):
            failures.append(f"BOM is forbidden in packaged text file: {name}")
    return failures


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


def _check_document_visual_distinction(zf: zipfile.ZipFile, names: set[str]) -> list[str]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for case_id in REQUIRED_CASES:
            rendered: dict[str, tuple[int, int, bytes]] = {}
            for doc in REQUIRED_DOCS:
                name = f"samples/{case_id}/{doc}.pdf"
                if name not in names:
                    continue
                rendered[doc] = _render_pdf_bytes(zf, name, tmp_dir)
            for left, right in (
                ("invoice", "purchase_order"),
                ("invoice", "goods_receipt"),
                ("purchase_order", "goods_receipt"),
            ):
                if left not in rendered or right not in rendered:
                    continue
                diff = _rms_diff(rendered[left], rendered[right])
                if diff < MIN_VISUAL_RMS_DIFF:
                    failures.append(
                        f"sample document types look too similar: {case_id} "
                        f"{left} vs {right} RMS={diff:.2f}"
                    )
    return failures


def _render_pdf_bytes(
    zf: zipfile.ZipFile,
    name: str,
    tmp_dir: Path,
) -> tuple[int, int, bytes]:
    pdf_path = tmp_dir / name.replace("/", "-")
    pdf_path.write_bytes(zf.read(name))
    document = fitz.open(pdf_path)
    try:
        page = document.load_page(0)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(0.12, 0.12), alpha=False)
        return pixmap.width, pixmap.height, bytes(pixmap.samples)
    finally:
        document.close()


def _rms_diff(left: tuple[int, int, bytes], right: tuple[int, int, bytes]) -> float:
    left_width, left_height, left_samples = left
    right_width, right_height, right_samples = right
    if (left_width, left_height) != (right_width, right_height):
        return 255.0
    if len(left_samples) != len(right_samples):
        return 255.0
    squared_error = sum((a - b) ** 2 for a, b in zip(left_samples, right_samples))
    return math.sqrt(squared_error / len(left_samples))


def _version_tuple(version: str) -> tuple[int, int, int]:
    parts = [int(part) for part in version.split(".")[:3]]
    while len(parts) < 3:
        parts.append(0)
    return (parts[0], parts[1], parts[2])


if __name__ == "__main__":
    main()
