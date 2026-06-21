from __future__ import annotations

from typing import Any


AUDIENCES = {"ap_operator", "approver", "procurement", "vendor"}
LANGUAGES = {"ja"}


def build_resolution_pack(
    completed_review: dict[str, Any],
    *,
    audience: str = "ap_operator",
    language: str = "ja",
) -> dict[str, Any]:
    if audience not in AUDIENCES:
        raise ValueError(f"Unsupported audience: {audience}")
    if language not in LANGUAGES:
        raise ValueError(f"Unsupported language: {language}")

    recommendation = str(completed_review.get("recommendation") or "UNKNOWN")
    context = _context(completed_review)
    template = _template(recommendation, context)
    messages = _messages(recommendation, context)

    return {
        "status": "RESOLUTION_PACK_BUILT",
        "run_id": completed_review.get("run_id"),
        "audience": audience,
        "language": language,
        "recommendation": recommendation,
        "recommendation_label_ja": completed_review.get("recommendation_label_ja"),
        "business_summary_ja": template["business_summary_ja"],
        "risk_level": template["risk_level"],
        "decision": {
            "payment_action": template["payment_action"],
            "can_pay_now": template["can_pay_now"],
            "external_write_performed": False,
        },
        "next_actions": template["next_actions"],
        "messages": messages,
        "evidence_refs": _evidence_refs(completed_review),
        "required_evidence": template["required_evidence"],
        "draft_payload_summary": {
            **dict(completed_review.get("draft_payload_summary") or {}),
            "payment_status": template["draft_payment_status"],
            "write_performed": False,
        },
        "artifact_paths": _safe_artifact_paths(completed_review),
        "safety_note_ja": "外部ERP/SaaSへの登録、支払実行、外部送信は行っていません。",
        "write_performed": False,
    }


def _context(completed_review: dict[str, Any]) -> dict[str, Any]:
    ocr = dict(completed_review.get("ocr_summary") or {})
    return {
        "invoice_number": ocr.get("invoice_number") or "対象請求書",
        "vendor_id": ocr.get("vendor_id") or "取引先",
        "po_number": ocr.get("po_number") or "対象PO",
        "invoice_total": ocr.get("invoice_total"),
        "purchase_order_total": ocr.get("purchase_order_total"),
        "received_quantity": ocr.get("received_quantity"),
        "rule_ids": list(completed_review.get("rule_ids") or []),
        "exception_summary_ja": completed_review.get("exception_summary_ja") or "主要照合項目を確認してください。",
    }


def _template(recommendation: str, context: dict[str, Any]) -> dict[str, Any]:
    invoice_number = context["invoice_number"]
    if recommendation == "PAY_READY_CANDIDATE":
        return {
            "risk_level": "low",
            "payment_action": "ready_to_pay",
            "can_pay_now": True,
            "draft_payment_status": "draft_ready",
            "business_summary_ja": (
                f"請求書 {invoice_number} は主要照合項目が一致しています。"
                "人間承認後の支払候補として扱えます。"
            ),
            "next_actions": [
                {
                    "owner": "ap_operator",
                    "action_ja": "支払候補として承認フローへ回す",
                    "due_hint_ja": "通常の支払承認期限まで",
                    "required_evidence": ["invoice", "purchase order", "goods receipt"],
                }
            ],
            "required_evidence": ["invoice", "purchase order", "goods receipt"],
        }
    if recommendation == "REFER_PO_MISMATCH":
        return {
            "risk_level": "medium",
            "payment_action": "hold",
            "can_pay_now": False,
            "draft_payment_status": "draft_hold",
            "business_summary_ja": (
                f"請求書 {invoice_number} は発注書との差異があります。"
                "支払前に購買担当へ変更POまたは承認済み差額の有無を確認してください。"
            ),
            "next_actions": [
                {
                    "owner": "procurement",
                    "action_ja": "PO変更有無と承認済み変更POの存在を確認する",
                    "due_hint_ja": "支払予定日前まで",
                    "required_evidence": ["approved revised PO", "buyer confirmation"],
                }
            ],
            "required_evidence": ["approved revised PO", "buyer confirmation"],
        }
    if recommendation == "REFER_DUPLICATE_REVIEW":
        return {
            "risk_level": "high",
            "payment_action": "hold",
            "can_pay_now": False,
            "draft_payment_status": "draft_hold",
            "business_summary_ja": (
                f"請求書 {invoice_number} は重複請求の可能性があります。"
                "過去請求と支払履歴を確認するまで支払保留候補です。"
            ),
            "next_actions": [
                {
                    "owner": "ap_operator",
                    "action_ja": "過去請求、支払済み履歴、訂正請求の有無を確認する",
                    "due_hint_ja": "支払処理前",
                    "required_evidence": ["invoice history", "payment status", "vendor confirmation if needed"],
                }
            ],
            "required_evidence": ["invoice history", "payment status"],
        }
    if recommendation == "REFER_VENDOR_REVIEW":
        return {
            "risk_level": "high",
            "payment_action": "hold",
            "can_pay_now": False,
            "draft_payment_status": "draft_hold",
            "business_summary_ja": (
                f"請求書 {invoice_number} は取引先または支払先情報の確認が必要です。"
                "取引先マスタ管理者の確認が完了するまで支払保留候補です。"
            ),
            "next_actions": [
                {
                    "owner": "vendor_master_owner",
                    "action_ja": "取引先マスタと請求書記載の支払先情報を照合する",
                    "due_hint_ja": "支払処理前",
                    "required_evidence": ["vendor master approval", "bank account change evidence"],
                }
            ],
            "required_evidence": ["vendor master approval", "bank account change evidence"],
        }
    if recommendation == "REFER_TAX_REVIEW":
        return {
            "risk_level": "medium",
            "payment_action": "hold",
            "can_pay_now": False,
            "draft_payment_status": "draft_hold",
            "business_summary_ja": (
                f"請求書 {invoice_number} は税額または税区分の確認が必要です。"
                "税務・経理担当の確認後に再レビューしてください。"
            ),
            "next_actions": [
                {
                    "owner": "tax_ap",
                    "action_ja": "税コード、税率、税額計算の妥当性を確認する",
                    "due_hint_ja": "計上前",
                    "required_evidence": ["tax code master", "tax calculation note"],
                }
            ],
            "required_evidence": ["tax code master", "tax calculation note"],
        }
    return {
        "risk_level": "medium",
        "payment_action": "manual_review",
        "can_pay_now": False,
        "draft_payment_status": "draft_hold",
        "business_summary_ja": (
            f"請求書 {invoice_number} は手動確認が必要です。"
            "不足情報と適用ルールを確認してください。"
        ),
        "next_actions": [
            {
                "owner": "ap_operator",
                "action_ja": "レビュー結果、根拠、不足情報を確認し、必要な担当者へ照会する",
                "due_hint_ja": "支払処理前",
                "required_evidence": ["review evidence"],
            }
        ],
        "required_evidence": ["review evidence"],
    }


def _messages(recommendation: str, context: dict[str, Any]) -> dict[str, str]:
    invoice_number = context["invoice_number"]
    po_number = context["po_number"]
    no_write = "なお、本MCPBは外部ERP/SaaSへの登録や支払実行を行っていません。"
    if recommendation == "REFER_PO_MISMATCH":
        procurement = (
            f"購買担当者様\n請求書 {invoice_number} について、PO {po_number} との差異が検出されています。"
            "変更POまたは承認済み差額の有無をご確認ください。"
            f"\n{no_write}"
        )
        vendor = (
            f"お取引先様\n請求書 {invoice_number} について、発注書との差異確認中です。"
            "必要に応じて修正版請求書または補足資料の提出をお願いする可能性があります。"
            f"\n{no_write}"
        )
        approver = "本件はPO差異のため現時点では支払保留候補です。購買担当確認後に再レビューしてください。"
    elif recommendation == "REFER_DUPLICATE_REVIEW":
        procurement = (
            f"購買担当者様\n請求書 {invoice_number} について重複請求の可能性があります。"
            "再発行または訂正請求か確認できる情報があれば共有してください。"
            f"\n{no_write}"
        )
        vendor = (
            f"お取引先様\n請求書 {invoice_number} について、過去請求との重複可能性を確認しています。"
            "再発行・訂正請求の場合はその旨と関連請求番号をご連絡ください。"
            f"\n{no_write}"
        )
        approver = "本件は重複疑いのため、支払履歴確認が完了するまで支払保留候補です。"
    elif recommendation == "REFER_VENDOR_REVIEW":
        procurement = (
            f"購買/取引先管理担当者様\n請求書 {invoice_number} の取引先または支払先情報について、"
            "取引先マスタとの差異が検出されています。登録情報と承認証跡をご確認ください。"
            f"\n{no_write}"
        )
        vendor = (
            f"お取引先様\n請求書 {invoice_number} の支払先情報について確認中です。"
            "必要に応じて正式な変更依頼書または証跡の提出をお願いする可能性があります。"
            f"\n{no_write}"
        )
        approver = "本件は取引先・支払先確認が必要なため、確認完了まで支払保留候補です。"
    elif recommendation == "PAY_READY_CANDIDATE":
        procurement = (
            f"購買担当者様\n請求書 {invoice_number} は主要照合項目が一致しています。"
            "追加の購買確認事項は現時点ではありません。"
            f"\n{no_write}"
        )
        vendor = (
            f"お取引先様\n請求書 {invoice_number} は確認中です。"
            "現時点で追加資料依頼はありません。"
            f"\n{no_write}"
        )
        approver = "主要照合項目は一致しています。人間承認後の支払候補として確認してください。"
    else:
        procurement = f"関係者様\n請求書 {invoice_number} について手動確認が必要です。\n{no_write}"
        vendor = f"お取引先様\n請求書 {invoice_number} について確認中です。\n{no_write}"
        approver = "本件は手動確認が必要です。根拠と不足情報を確認してください。"
    return {
        "to_procurement_ja": procurement,
        "to_vendor_ja": vendor,
        "to_approver_ja": f"{approver}\n{no_write}",
    }


def _evidence_refs(completed_review: dict[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for evidence in completed_review.get("evidence") or []:
        refs.append(
            {
                "source": evidence.get("document_type"),
                "field": evidence.get("field_label"),
                "value": evidence.get("normalized_value"),
                "page": evidence.get("page"),
            }
        )
    return refs


def _safe_artifact_paths(completed_review: dict[str, Any]) -> dict[str, str]:
    paths = dict(completed_review.get("artifact_paths") or {})
    return {key: value for key, value in paths.items() if key in {"ocr_results", "decision_result", "draft_payloads"}}
