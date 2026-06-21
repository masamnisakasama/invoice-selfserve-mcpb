from __future__ import annotations

import os
import subprocess
import sys
import time
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DIST = PROJECT_ROOT / "dist"
OUTPUT = DIST / "ap-invoice-review.mcpb"
SAMPLE_LOCK = DIST / ".sample-generation.lock"
SAMPLE_LOCK_ENV = "AP_SAMPLE_GENERATION_LOCKED"
LOCK_POLL_SECONDS = 0.2
LOCK_TIMEOUT_SECONDS = 120.0
ZIP_TIMESTAMP = (2026, 1, 1, 0, 0, 0)

INCLUDE_DIRS = [
    ".claude",
    "ap_invoice_core",
    "ap_invoice_mcp",
    "workflow-packs",
    "samples",
    "docs",
    "enterprise-bundle/plugin/ap-invoice-review",
    "commands",
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
EXCLUDE_PATHS = {
    "docs/HANDOFF_SESSION3.md",
    "docs/codex-task.md",
}
NO_BOM_FILES = (
    ".claude-plugin/plugin.json",
    ".claude/commands/ap-review.md",
    ".claude/skills/ap-review/SKILL.md",
    "commands/ap-review.md",
    "manifest.json",
    "workflow-packs/ap-invoice-v1/SKILL.md",
)
BOM = b"\xef\xbb\xbf"


def ensure_samples() -> None:
    env = os.environ.copy()
    env[SAMPLE_LOCK_ENV] = "1"
    subprocess.run(
        [sys.executable, "scripts/generate_ap_samples.py"],
        cwd=PROJECT_ROOT,
        check=True,
        env=env,
    )


def acquire_sample_lock() -> None:
    DIST.mkdir(exist_ok=True)
    deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
    while True:
        try:
            SAMPLE_LOCK.mkdir()
            (SAMPLE_LOCK / "pid").write_text(str(os.getpid()), encoding="ascii")
            return
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise SystemExit(f"Timed out waiting for sample generation lock: {SAMPLE_LOCK}")
            time.sleep(LOCK_POLL_SECONDS)


def release_sample_lock() -> None:
    pid_file = SAMPLE_LOCK / "pid"
    if pid_file.exists():
        pid_file.unlink()
    if SAMPLE_LOCK.exists():
        SAMPLE_LOCK.rmdir()


def should_skip(path: Path) -> bool:
    relative = path.relative_to(PROJECT_ROOT)
    return relative.as_posix() in EXCLUDE_PATHS or any(part in SKIP_PARTS for part in relative.parts)


def add_path(zf: zipfile.ZipFile, path: Path) -> None:
    if path.is_dir():
        for child in sorted(path.rglob("*")):
            if child.is_file() and not should_skip(child):
                write_file(zf, child, child.relative_to(PROJECT_ROOT).as_posix())
    elif path.is_file() and not should_skip(path):
        write_file(zf, path, path.relative_to(PROJECT_ROOT).as_posix())


def add_claude_plugin_aliases(zf: zipfile.ZipFile) -> None:
    write_file(zf, PROJECT_ROOT / ".claude-plugin" / "plugin.json", ".claude-plugin/plugin.json")
    write_file(
        zf,
        PROJECT_ROOT / "workflow-packs" / "ap-invoice-v1" / "SKILL.md",
        "skills/ap-review/SKILL.md",
    )


def write_file(zf: zipfile.ZipFile, path: Path, arcname: str) -> None:
    info = zipfile.ZipInfo(arcname, ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    zf.writestr(info, path.read_bytes())


def assert_no_bom() -> None:
    for file_name in NO_BOM_FILES:
        path = PROJECT_ROOT / file_name
        if path.is_file() and path.read_bytes().startswith(BOM):
            raise SystemExit(f"BOM is forbidden: {file_name}")


def main() -> None:
    assert_no_bom()
    DIST.mkdir(exist_ok=True)
    acquire_sample_lock()
    try:
        ensure_samples()
        if OUTPUT.exists():
            OUTPUT.unlink()
        with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for file_name in INCLUDE_FILES:
                add_path(zf, PROJECT_ROOT / file_name)
            for dir_name in INCLUDE_DIRS:
                add_path(zf, PROJECT_ROOT / dir_name)
            add_claude_plugin_aliases(zf)
    finally:
        release_sample_lock()
    print(f"Created {OUTPUT}")


if __name__ == "__main__":
    main()
