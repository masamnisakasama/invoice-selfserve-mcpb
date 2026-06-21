from __future__ import annotations

import json
from pathlib import Path

from tests.helpers import load_expected, review_case


def test_golden_decision_artifacts_match_expected_case_results(tmp_path: Path) -> None:
    for case_name in (
        "case-a-pay-ready",
        "case-b-po-mismatch",
        "case-c-duplicate",
        "case-d-vendor-review",
    ):
        expected = load_expected(case_name)
        reviewed = review_case(case_name, tmp_path / "artifacts" / case_name)
        result = reviewed["result"]
        artifacts = result["audit_artifacts"]

        decision_path = Path(artifacts["decision_result_uri"])
        rules_path = Path(artifacts["rule_result_uri"])
        trace_path = Path(artifacts["execution_trace_uri"])
        for path in (decision_path, rules_path, trace_path):
            assert path.is_file()

        decision = json.loads(decision_path.read_text("utf-8"))
        rules = json.loads(rules_path.read_text("utf-8"))
        assert decision["recommendation"] == expected["recommendation"]
        assert decision["write_performed"] is False
        assert [rule["rule_id"] for rule in rules] == expected["rule_ids"]


def test_draft_payload_snapshot_is_draft_only(tmp_path: Path) -> None:
    reviewed = review_case("case-a-pay-ready", tmp_path / "artifacts")
    result = reviewed["result"]
    generic = result["draft_payloads"]["generic_ap"]
    assert generic == {
        "vendor_id": "V-1001",
        "invoice_number": "INV-2026-0008",
        "invoice_date": "2026-07-15",
        "due_date": "2026-08-14",
        "currency": "JPY",
        "subtotal_amount": 100000,
        "tax_amount": 10000,
        "total_amount": 110000,
        "po_number": "PO-2026-0001",
        "cost_center": "CC-ADMIN",
        "payment_status": "draft",
        "source_case_id": reviewed["case_id"],
        "write_performed": False,
    }
