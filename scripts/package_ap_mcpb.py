from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DIST = PROJECT_ROOT / "dist"
OUTPUT = DIST / "ap-invoice-review.mcpb"

INCLUDE_DIRS = [
    "ap_invoice_core",
    "ap_invoice_mcp",
    "workflow-packs",
    "samples",
    "docs",
    "enterprise-bundle/plugin/ap-invoice-review",
]
INCLUDE_FILES = [
    "manifest.json",
    "README.md",
    "pyproject.toml",
    "uv.lock",
]

SKIP_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "artifacts",
    "dist",
}


def ensure_samples() -> None:
    subprocess.run([sys.executable, "scripts/generate_ap_samples.py"], cwd=PROJECT_ROOT, check=True)


def should_skip(path: Path) -> bool:
    return any(part in SKIP_PARTS for part in path.relative_to(PROJECT_ROOT).parts)


def add_path(zf: zipfile.ZipFile, path: Path) -> None:
    if path.is_dir():
        for child in sorted(path.rglob("*")):
            if child.is_file() and not should_skip(child):
                zf.write(child, child.relative_to(PROJECT_ROOT).as_posix())
    elif path.is_file() and not should_skip(path):
        zf.write(path, path.relative_to(PROJECT_ROOT).as_posix())


def main() -> None:
    ensure_samples()
    DIST.mkdir(exist_ok=True)
    if OUTPUT.exists():
        OUTPUT.unlink()
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_name in INCLUDE_FILES:
            add_path(zf, PROJECT_ROOT / file_name)
        for dir_name in INCLUDE_DIRS:
            add_path(zf, PROJECT_ROOT / dir_name)
    print(f"Created {OUTPUT}")


if __name__ == "__main__":
    main()
