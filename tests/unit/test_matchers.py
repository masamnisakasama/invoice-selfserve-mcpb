from __future__ import annotations

from ap_invoice_core.extraction import load_canonical_from_documents
from ap_invoice_core.matchers import duplicate_score, match_vendor_master, tax_check
from ap_invoice_core.reference import ReferenceData
from scripts.generate_ap_samples import main as generate_samples
from tests.helpers import PROJECT_ROOT, SAMPLES_DIR


def test_vendor_master_matches_pay_ready_fixture() -> None:
    generate_samples()
    facts = load_canonical_from_documents(
        invoice_pdf=SAMPLES_DIR / "case-a-pay-ready" / "invoice.pdf",
        purchase_order_pdf=SAMPLES_DIR / "case-a-pay-ready" / "purchase_order.pdf",
        goods_receipt_pdf=SAMPLES_DIR / "case-a-pay-ready" / "goods_receipt.pdf",
    )
    result = match_vendor_master(facts, ReferenceData(PROJECT_ROOT / "workflow-packs" / "ap-invoice-v1"))
    assert result.status == "matched"
    assert result.details["bank_account_match"] is True


def test_duplicate_score_detects_known_history_invoice() -> None:
    generate_samples()
    facts = load_canonical_from_documents(
        invoice_pdf=SAMPLES_DIR / "case-c-duplicate" / "invoice.pdf",
        purchase_order_pdf=SAMPLES_DIR / "case-c-duplicate" / "purchase_order.pdf",
        goods_receipt_pdf=SAMPLES_DIR / "case-c-duplicate" / "goods_receipt.pdf",
    )
    result = duplicate_score(facts, ReferenceData(PROJECT_ROOT / "workflow-packs" / "ap-invoice-v1"))
    assert result.status == "candidate"
    assert result.details["score"] == 100


def test_tax_check_uses_master_rate_and_rounding_tolerance() -> None:
    generate_samples()
    facts = load_canonical_from_documents(
        invoice_pdf=SAMPLES_DIR / "case-a-pay-ready" / "invoice.pdf",
        purchase_order_pdf=SAMPLES_DIR / "case-a-pay-ready" / "purchase_order.pdf",
        goods_receipt_pdf=SAMPLES_DIR / "case-a-pay-ready" / "goods_receipt.pdf",
    )
    result = tax_check(
        facts,
        ReferenceData(PROJECT_ROOT / "workflow-packs" / "ap-invoice-v1"),
        rounding_tolerance=1,
    )
    assert result.status == "matched"
    assert result.details["tax_diff"] == 0
