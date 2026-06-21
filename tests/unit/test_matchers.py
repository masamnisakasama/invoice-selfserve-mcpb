from __future__ import annotations

from ap_invoice_core.extraction import canonical_from_ocr_results
from ap_invoice_core.matchers import duplicate_score, match_vendor_master, tax_check
from ap_invoice_core.reference import ReferenceData
from scripts.generate_ap_samples import main as generate_samples
from tests.helpers import PROJECT_ROOT, ocr_results_for_case


def facts_for_case(case_name: str):
    ocr = ocr_results_for_case(case_name)
    return canonical_from_ocr_results(
        invoice_ocr=ocr["invoice"],
        purchase_order_ocr=ocr["purchase_order"],
        goods_receipt_ocr=ocr["goods_receipt"],
    )


def test_vendor_master_matches_pay_ready_fixture() -> None:
    generate_samples()
    facts = facts_for_case("case-a-pay-ready")
    result = match_vendor_master(facts, ReferenceData(PROJECT_ROOT / "workflow-packs" / "ap-invoice-v1"))
    assert result.status == "matched"
    assert result.details["bank_account_match"] is True


def test_duplicate_score_detects_known_history_invoice() -> None:
    generate_samples()
    facts = facts_for_case("case-c-duplicate")
    result = duplicate_score(facts, ReferenceData(PROJECT_ROOT / "workflow-packs" / "ap-invoice-v1"))
    assert result.status == "candidate"
    assert result.details["score"] == 100


def test_tax_check_uses_master_rate_and_rounding_tolerance() -> None:
    generate_samples()
    facts = facts_for_case("case-a-pay-ready")
    result = tax_check(
        facts,
        ReferenceData(PROJECT_ROOT / "workflow-packs" / "ap-invoice-v1"),
        rounding_tolerance=1,
    )
    assert result.status == "matched"
    assert result.details["tax_diff"] == 0
