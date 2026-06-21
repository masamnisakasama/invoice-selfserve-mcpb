from __future__ import annotations

import pytest

from ap_invoice_core.resolution import build_resolution_pack
from tests.helpers import review_case


def test_resolution_pack_pay_ready_candidate(tmp_path):
    reviewed = review_case("case-a-pay-ready", tmp_path / "artifacts")

    pack = reviewed["service"].build_resolution_pack(run_id=reviewed["run_id"])

    assert pack["status"] == "RESOLUTION_PACK_BUILT"
    assert pack["recommendation"] == "PAY_READY_CANDIDATE"
    assert pack["decision"]["payment_action"] == "ready_to_pay"
    assert pack["decision"]["can_pay_now"] is True
    assert pack["write_performed"] is False
    assert pack["draft_payload_summary"]["write_performed"] is False


def test_resolution_pack_po_mismatch_has_procurement_message(tmp_path):
    reviewed = review_case("case-b-po-mismatch", tmp_path / "artifacts")

    pack = reviewed["service"].build_resolution_pack(run_id=reviewed["run_id"])

    assert pack["recommendation"] == "REFER_PO_MISMATCH"
    assert pack["decision"]["payment_action"] == "hold"
    assert pack["decision"]["can_pay_now"] is False
    assert pack["risk_level"] == "medium"
    assert pack["next_actions"][0]["owner"] == "procurement"
    assert "変更PO" in pack["messages"]["to_procurement_ja"]
    assert "外部ERP/SaaSへの登録" in pack["safety_note_ja"]


def test_resolution_pack_duplicate_has_history_review_action(tmp_path):
    reviewed = review_case("case-c-duplicate", tmp_path / "artifacts")

    pack = reviewed["service"].build_resolution_pack(run_id=reviewed["run_id"])

    assert pack["recommendation"] == "REFER_DUPLICATE_REVIEW"
    assert pack["risk_level"] == "high"
    assert pack["next_actions"][0]["owner"] == "ap_operator"
    assert "過去請求" in pack["next_actions"][0]["action_ja"]
    assert "重複" in pack["messages"]["to_approver_ja"]


def test_resolution_pack_vendor_review_has_vendor_master_action(tmp_path):
    reviewed = review_case("case-d-vendor-review", tmp_path / "artifacts")

    pack = reviewed["service"].build_resolution_pack(run_id=reviewed["run_id"])

    assert pack["recommendation"] == "REFER_VENDOR_REVIEW"
    assert pack["risk_level"] == "high"
    assert pack["next_actions"][0]["owner"] == "vendor_master_owner"
    assert "取引先マスタ" in pack["next_actions"][0]["action_ja"]
    assert "支払先情報" in pack["messages"]["to_vendor_ja"]


def test_resolution_pack_unknown_recommendation_falls_back_to_manual_review():
    pack = build_resolution_pack(
        {
            "run_id": "ocr-run-test",
            "recommendation": "SOMETHING_NEW",
            "ocr_summary": {"invoice_number": "INV-X"},
            "draft_payload_summary": {"payment_status": "draft"},
            "artifact_paths": {},
            "evidence": [],
        }
    )

    assert pack["decision"]["payment_action"] == "manual_review"
    assert pack["decision"]["can_pay_now"] is False
    assert pack["write_performed"] is False


def test_resolution_pack_rejects_unsupported_language(tmp_path):
    reviewed = review_case("case-a-pay-ready", tmp_path / "artifacts")

    with pytest.raises(ValueError, match="Unsupported language"):
        reviewed["service"].build_resolution_pack(run_id=reviewed["run_id"], language="en")


def test_resolution_pack_messages_do_not_claim_external_write(tmp_path):
    reviewed = review_case("case-b-po-mismatch", tmp_path / "artifacts")
    pack = reviewed["service"].build_resolution_pack(run_id=reviewed["run_id"])

    joined = "\n".join(pack["messages"].values())
    assert "登録しました" not in joined
    assert "支払実行しました" not in joined
    assert "送信しました" not in joined
    assert "write_performed" in pack
    assert pack["write_performed"] is False
