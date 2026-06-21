from __future__ import annotations

import sys
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    failures: list[str] = []
    failures.extend(_local_forbidden_json(PROJECT_ROOT / "samples"))
    failures.extend(_local_forbidden_json(PROJECT_ROOT / "workflow-packs" / "ap-invoice-v1" / "samples"))
    if len(sys.argv) > 1:
        failures.extend(_bundle_forbidden_json(Path(sys.argv[1])))
    if failures:
        for failure in failures:
            print(failure)
        raise SystemExit(1)
    print("No answer sidecars found.")


def _local_forbidden_json(root: Path) -> list[str]:
    if not root.exists():
        return []
    return [f"forbidden sample JSON: {path}" for path in sorted(root.rglob("*.json"))]


def _bundle_forbidden_json(bundle: Path) -> list[str]:
    if not bundle.is_file():
        return [f"bundle not found: {bundle}"]
    failures: list[str] = []
    with zipfile.ZipFile(bundle) as zf:
        for name in zf.namelist():
            if name.endswith(".json") and (
                name.startswith("samples/")
                or name.startswith("workflow-packs/ap-invoice-v1/samples/")
            ):
                failures.append(f"forbidden bundled sample JSON: {name}")
    return failures


if __name__ == "__main__":
    main()
