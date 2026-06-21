from __future__ import annotations

import math
from pathlib import Path

import fitz
import pytest

from tests.helpers import SAMPLES_DIR, ensure_samples, load_expected, review_case


CASES = [
    "case-a-pay-ready",
    "case-b-po-mismatch",
    "case-c-duplicate",
    "case-d-vendor-review",
    "case-e-grn-mismatch",
    "case-f-tax-review",
]
DOCS = ("invoice", "purchase_order", "goods_receipt")
MIN_VISUAL_RMS_DIFF = 18.0


@pytest.mark.parametrize("case_name", CASES)
def test_ap_fixture_recommendations_are_stable(case_name: str, tmp_path: Path) -> None:
    expected = load_expected(case_name)
    reviewed = review_case(case_name, tmp_path / "artifacts")
    result = reviewed["result"]

    assert result["recommendation"] == expected["recommendation"]
    assert [rule["rule_id"] for rule in result["rule_results"]] == expected["rule_ids"]
    assert result["write_performed"] is False
    assert result["draft_payloads"]["generic_ap"]["write_performed"] is False
    assert result["draft_payloads"]["freee"]["write_performed"] is False
    assert result["draft_payloads"]["kintone_review_record"]["write_performed"] is False
    assert reviewed["draft"]["write_performed"] is False


def test_case_b_explains_po_amount_difference(tmp_path: Path) -> None:
    result = review_case("case-b-po-mismatch", tmp_path / "artifacts")["result"]
    po_match = result["match_results"]["po_match"]
    assert po_match["status"] == "mismatch"
    assert po_match["details"]["amount_diff"] == 11000
    assert po_match["details"]["within_tolerance"] is False


@pytest.mark.parametrize("case_name", CASES)
def test_fixture_pdfs_are_distinct_form_designs(case_name: str) -> None:
    ensure_samples()
    rendered = {
        doc: _render_pdf_bytes(SAMPLES_DIR / case_name / f"{doc}.pdf")
        for doc in DOCS
    }

    for left, right in (
        ("invoice", "purchase_order"),
        ("invoice", "goods_receipt"),
        ("purchase_order", "goods_receipt"),
    ):
        diff = _rms_diff(rendered[left], rendered[right])
        assert diff >= MIN_VISUAL_RMS_DIFF, f"{case_name}: {left} vs {right} RMS={diff:.2f}"


def _render_pdf_bytes(path: Path) -> tuple[int, int, bytes]:
    document = fitz.open(path)
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
    squared_error = sum((a - b) ** 2 for a, b in zip(left_samples, right_samples))
    return math.sqrt(squared_error / len(left_samples))
