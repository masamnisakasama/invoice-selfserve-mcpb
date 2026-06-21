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
        artifact_dir = tmp_path / "artifacts" / case_name / reviewed["case_id"]

        decision_path = artifact_dir / "decision_result.json"
        rules_path = artifact_dir / "rule_result.json"
        trace_path = artifact_dir / "execution_trace.json"
        for path in (decision_path, rules_path, trace_path):
            assert path.is_file()
        for uri in result["audit_artifacts"].values():
            assert uri.startswith(f"artifact://{reviewed['case_id']}/")

        decision = json.loads(decision_path.read_text("utf-8"))
        rules = json.loads(rules_path.read_text("utf-8"))
        assert decision["recommendation"] == expected["recommendation"]
        assert decision["write_performed"] is False
        assert [rule["rule_id"] for rule in rules] == expected["rule_ids"]


def test_v2_expected_decision_snapshots(tmp_path: Path) -> None:
    for case_name in (
        "case-a-pay-ready",
        "case-b-po-mismatch",
        "case-c-duplicate",
        "case-d-vendor-review",
    ):
        expected_path = Path(__file__).parent / case_name / "expected_decision.json"
        expected = json.loads(expected_path.read_text("utf-8"))
        result = review_case(case_name, tmp_path / "artifacts" / case_name)["result"]

        assert result["recommendation"] == expected["recommendation"]
        assert [rule["rule_id"] for rule in result["rule_results"]] == expected["rule_ids"]
        assert {
            key: value["status"] for key, value in result["match_results"].items()
        } == expected["match_status"]
        assert result["write_performed"] == expected["write_performed"]
        assert result["draft_payloads"]["generic_ap"]["write_performed"] is False
        assert result["audit_artifacts"]


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
