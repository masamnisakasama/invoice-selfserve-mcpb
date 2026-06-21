from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from .models import CanonicalFacts, MatchResult
from .reference import ReferenceData


def _bool(value: Any) -> bool:
    return str(value).lower() in {"true", "1", "yes", "y"}


def match_vendor_master(facts: CanonicalFacts, refs: ReferenceData) -> MatchResult:
    vendor_id = str(facts.invoice.vendor_id.value)
    vendor = refs.vendor_master.get(vendor_id)
    evidence = facts.invoice.vendor_id.evidence + facts.invoice.bank_account.evidence
    if vendor is None:
        return MatchResult(
            match_type="vendor_master",
            status="not_found",
            details={"vendor_id": vendor_id},
            evidence=evidence,
        )
    status = "matched"
    details = {
        "vendor_id": vendor_id,
        "bank_account_match": str(facts.invoice.bank_account.value) == vendor["bank_account"],
        "blocked": _bool(vendor.get("blocked")),
        "tax_category_match": str(facts.invoice.tax_code.value) == vendor.get("tax_category"),
        "payment_terms": vendor.get("payment_terms"),
        "master": vendor,
    }
    if not details["bank_account_match"] or details["blocked"]:
        status = "mismatch"
    return MatchResult(
        match_type="vendor_master",
        status=status,
        details=details,
        evidence=evidence,
    )


def match_purchase_order(
    facts: CanonicalFacts,
    refs: ReferenceData,
    amount_tolerance_jpy: float,
) -> MatchResult:
    po_number = str(facts.invoice.po_number.value)
    po = refs.po_master.get(po_number)
    evidence = facts.invoice.total_amount.evidence + facts.purchase_order.total_amount.evidence
    if po is None:
        return MatchResult(match_type="po_match", status="not_found", details={"po_number": po_number}, evidence=evidence)
    invoice_total = float(facts.invoice.total_amount.value)
    po_total = float(facts.purchase_order.total_amount.value)
    diff = invoice_total - po_total
    details = {
        "po_number": po_number,
        "approved": _bool(po.get("approved")) and bool(facts.purchase_order.approved.value),
        "vendor_id_match": str(facts.invoice.vendor_id.value) == str(facts.purchase_order.vendor_id.value),
        "currency_match": str(facts.invoice.currency.value) == str(facts.purchase_order.currency.value),
        "invoice_total": invoice_total,
        "po_total": po_total,
        "amount_diff": diff,
        "within_tolerance": abs(diff) <= amount_tolerance_jpy,
        "remaining_balance_sufficient": invoice_total <= float(facts.purchase_order.remaining_balance.value),
    }
    status = "matched" if all(
        [
            details["approved"],
            details["vendor_id_match"],
            details["currency_match"],
            details["within_tolerance"],
            details["remaining_balance_sufficient"],
        ]
    ) else "mismatch"
    return MatchResult(match_type="po_match", status=status, details=details, evidence=evidence)


def match_goods_receipt(facts: CanonicalFacts) -> MatchResult:
    invoice_qty = facts.invoice.total_quantity
    received_qty = float(facts.goods_receipt.received_quantity.value)
    evidence = facts.goods_receipt.received_quantity.evidence
    details = {
        "received": bool(facts.goods_receipt.received.value),
        "invoice_quantity": invoice_qty,
        "received_quantity": received_qty,
        "quantity_covered": received_qty >= invoice_qty,
        "po_number_match": str(facts.invoice.po_number.value) == str(facts.goods_receipt.po_number.value),
    }
    status = "matched" if all(details.values()) else "mismatch"
    return MatchResult(match_type="grn_match", status=status, details=details, evidence=evidence)


def duplicate_score(facts: CanonicalFacts, refs: ReferenceData) -> MatchResult:
    invoice = facts.invoice
    best_score = 0
    best_reason = ""
    best_row: dict[str, Any] | None = None
    invoice_date = date.fromisoformat(str(invoice.invoice_date.value))
    for row in refs.invoice_history:
        score = 0
        reason = ""
        if row["vendor_id"] == invoice.vendor_id.value and row["invoice_number"] == invoice.invoice_number.value:
            score = 100
            reason = "vendor_id + invoice_number"
        elif row["vendor_id"] == invoice.vendor_id.value and float(row["total_amount"]) == float(invoice.total_amount.value):
            history_date = date.fromisoformat(row["invoice_date"])
            if abs((history_date - invoice_date).days) <= 7:
                score = 90
                reason = "vendor_id + total_amount + invoice_date ± 7 days"
        elif row["bank_account"] == invoice.bank_account.value and float(row["total_amount"]) == float(invoice.total_amount.value):
            score = 80
            reason = "bank_account + total_amount"
        if score > best_score:
            best_score = score
            best_reason = reason
            best_row = row
    return MatchResult(
        match_type="duplicate_check",
        status="candidate" if best_score >= 80 else "clear",
        details={"score": best_score, "reason": best_reason, "matched_invoice": best_row},
        evidence=invoice.invoice_number.evidence + invoice.total_amount.evidence,
    )


def tax_check(facts: CanonicalFacts, refs: ReferenceData, rounding_tolerance: float) -> MatchResult:
    tax_code = str(facts.invoice.tax_code.value)
    tax = refs.tax_code_master.get(tax_code)
    evidence = facts.invoice.tax_amount.evidence + facts.invoice.tax_code.evidence
    if tax is None:
        return MatchResult(match_type="tax_check", status="not_found", details={"tax_code": tax_code}, evidence=evidence)
    expected = round(float(facts.invoice.subtotal_amount.value) * float(tax["rate"]))
    actual = float(facts.invoice.tax_amount.value)
    diff = actual - expected
    return MatchResult(
        match_type="tax_check",
        status="matched" if abs(diff) <= rounding_tolerance else "mismatch",
        details={"tax_code": tax_code, "expected_tax": expected, "actual_tax": actual, "tax_diff": diff},
        evidence=evidence,
    )


def receipt_due_date(invoice_date: str, days: int = 30) -> str:
    return (date.fromisoformat(invoice_date) + timedelta(days=days)).isoformat()

