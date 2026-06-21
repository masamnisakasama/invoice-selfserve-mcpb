from __future__ import annotations

import sys
import zipfile
from pathlib import Path


FORBIDDEN_FILENAME_PARTS = {
    ".env",
    "credentials",
    "id_rsa",
    "private_key",
    "__pycache__",
}

FORBIDDEN_TEXT = [
    "AWS_SECRET_ACCESS_KEY",
    "BEGIN PRIVATE KEY",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "DEMO_MCP_TOKEN",
    "freee_access_token",
    "kintone_api_token",
    '"write_performed": true',
]


def scan_zip(path: Path) -> list[str]:
    failures: list[str] = []
    with zipfile.ZipFile(path) as zf:
        for info in zf.infolist():
            lower_name = info.filename.lower()
            if any(part in lower_name for part in FORBIDDEN_FILENAME_PARTS):
                failures.append(f"forbidden filename: {info.filename}")
            if info.file_size > 2_000_000:
                continue
            try:
                text = zf.read(info).decode("utf-8")
            except UnicodeDecodeError:
                continue
            for token in FORBIDDEN_TEXT:
                if token in text:
                    failures.append(f"forbidden text {token!r} in {info.filename}")
    return failures


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_ap_data_boundary.py dist/ap-invoice-review.mcpb")
    bundle = Path(sys.argv[1])
    if not bundle.is_file():
        raise SystemExit(f"bundle not found: {bundle}")
    failures = scan_zip(bundle)
    if failures:
        for failure in failures:
            print(failure)
        raise SystemExit(1)
    print(f"Boundary check passed: {bundle}")


if __name__ == "__main__":
    main()
