from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Recommendation(str, Enum):
    PAY_READY_CANDIDATE = "PAY_READY_CANDIDATE"
    REFER_PO_MISMATCH = "REFER_PO_MISMATCH"
    REFER_GRN_MISMATCH = "REFER_GRN_MISMATCH"
    REFER_VENDOR_REVIEW = "REFER_VENDOR_REVIEW"
    REFER_DUPLICATE_REVIEW = "REFER_DUPLICATE_REVIEW"
    REFER_TAX_REVIEW = "REFER_TAX_REVIEW"
    REFER_INFO_REQUEST = "REFER_INFO_REQUEST"
    BLOCKED_CANDIDATE = "BLOCKED_CANDIDATE"

    @property
    def severity(self) -> int:
        return {
            "PAY_READY_CANDIDATE": 0,
            "REFER_INFO_REQUEST": 1,
            "REFER_GRN_MISMATCH": 2,
            "REFER_TAX_REVIEW": 2,
            "REFER_PO_MISMATCH": 3,
            "REFER_VENDOR_REVIEW": 4,
            "REFER_DUPLICATE_REVIEW": 5,
            "BLOCKED_CANDIDATE": 6,
        }[self.value]

    @property
    def label_ja(self) -> str:
        return {
            "PAY_READY_CANDIDATE": "支払候補",
            "REFER_PO_MISMATCH": "発注書差異確認",
            "REFER_GRN_MISMATCH": "納品/検収差異確認",
            "REFER_VENDOR_REVIEW": "取引先確認",
            "REFER_DUPLICATE_REVIEW": "重複請求確認",
            "REFER_TAX_REVIEW": "税務確認",
            "REFER_INFO_REQUEST": "追加情報依頼",
            "BLOCKED_CANDIDATE": "支払ブロック候補",
        }[self.value]


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_type: str
    document_name: str
    page: int = 1
    field_label: str
    raw_text: str
    normalized_value: Any = None
    bbox: list[int] | None = None
    source: str | None = None


class FieldValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: Any = None
    confidence: float = 1.0
    evidence: list[Evidence] = Field(default_factory=list)


class InvoiceLineItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str
    quantity: float
    unit_price: float
    amount: float
    tax_code: str


class InvoiceFacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invoice_number: FieldValue
    invoice_date: FieldValue
    due_date: FieldValue | None = None
    vendor_name: FieldValue
    vendor_id: FieldValue
    po_number: FieldValue
    currency: FieldValue
    subtotal_amount: FieldValue
    tax_amount: FieldValue
    total_amount: FieldValue
    bank_account: FieldValue
    tax_code: FieldValue
    cost_center: FieldValue | None = None
    line_items: list[InvoiceLineItem]

    @property
    def total_quantity(self) -> float:
        return sum(item.quantity for item in self.line_items)


class PurchaseOrderFacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    po_number: FieldValue
    vendor_id: FieldValue
    currency: FieldValue
    total_amount: FieldValue
    approved: FieldValue
    remaining_balance: FieldValue
    line_items: list[InvoiceLineItem]


class GoodsReceiptFacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    receipt_number: FieldValue
    po_number: FieldValue
    received: FieldValue
    received_quantity: FieldValue
    receipt_date: FieldValue


class CanonicalFacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invoice: InvoiceFacts
    purchase_order: PurchaseOrderFacts
    goods_receipt: GoodsReceiptFacts


class MatchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    match_type: str
    status: str
    details: dict[str, Any] = Field(default_factory=dict)
    evidence: list[Evidence] = Field(default_factory=list)


class RuleResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str
    category: str
    severity: str
    recommendation: Recommendation
    description: str
    evidence: list[Evidence] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)


class DraftPayloads(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generic_ap: dict[str, Any]
    freee: dict[str, Any]
    kintone_review_record: dict[str, Any]


class AuditArtifacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    canonical_facts_uri: str
    vendor_match_result_uri: str
    po_match_result_uri: str
    grn_match_result_uri: str
    duplicate_check_result_uri: str
    rule_result_uri: str
    decision_result_uri: str
    execution_trace_uri: str


class DecisionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    tenant_id: str
    workflow_pack: str
    ruleset_version: str
    recommendation: Recommendation
    recommendation_label_ja: str
    confidence: float
    summary: str
    exceptions: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    match_results: dict[str, MatchResult]
    rule_results: list[RuleResult]
    evidence: list[Evidence]
    draft_payloads: DraftPayloads
    audit_artifacts: AuditArtifacts
    write_performed: bool = False
