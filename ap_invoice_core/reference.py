from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


class ReferenceData:
    def __init__(self, pack_dir: str | Path) -> None:
        root = Path(pack_dir) / "reference_tables"
        self.vendor_master = _load_by_key(root / "vendor_master.csv", "vendor_id")
        self.po_master = _load_by_key(root / "po_master.csv", "po_number")
        self.goods_receipt_master = _load_by_key(
            root / "goods_receipt_master.csv", "receipt_number"
        )
        self.invoice_history = _load_rows(root / "invoice_history.csv")
        self.tax_code_master = _load_by_key(root / "tax_code_master.csv", "tax_code")
        self.cost_center_master = _load_by_key(root / "cost_center_master.csv", "cost_center")


def _load_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as fp:
        return [dict(row) for row in csv.DictReader(fp)]


def _load_by_key(path: Path, key: str) -> dict[str, dict[str, Any]]:
    return {str(row[key]): row for row in _load_rows(path)}

