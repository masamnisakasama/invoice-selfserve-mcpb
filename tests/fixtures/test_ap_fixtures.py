from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers import load_expected, review_case


CASES = [
    "case-a-pay-ready",
    "case-b-po-mismatch",
    "case-c-duplicate",
    "case-d-vendor-review",
    "case-e-grn-mismatch",
    "case-f-tax-review",
]


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
