from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .engine import RULESET_VERSION, WORKFLOW_PACK, review_invoice_packet
from .extraction import load_canonical_from_documents
from .models import DecisionResult, Evidence, Recommendation, RuleResult
from .ocr_smoke import (
    build_ocr_smoke_test,
    default_visible_workspace,
    submit_ocr_smoke_test_result,
)


DOCUMENT_TYPES = ("invoice", "purchase_order", "goods_receipt")
TARGET_SYSTEMS = ("generic_ap", "freee", "kintone_review_record")
AUDIENCES = ("ap_operator", "approver", "purchasing_owner", "vendor_contact")

DEMO_CASES: dict[str, dict[str, str]] = {
    "case-a-pay-ready": {
        "label_ja": "支払候補",
        "expected_recommendation": "PAY_READY_CANDIDATE",
        "business_value_ja": "請求書・PO・GRN・税額・重複なしが一致する正常系です。",
    },
    "case-b-po-mismatch": {
        "label_ja": "PO差異",
        "expected_recommendation": "REFER_PO_MISMATCH",
        "business_value_ja": "請求額がPO許容差を超過するケースです。",
    },
    "case-c-duplicate": {
        "label_ja": "重複請求疑い",
        "expected_recommendation": "REFER_DUPLICATE_REVIEW",
        "business_value_ja": "過去請求との重複疑いを検出し、二重払いを防ぐケースです。",
    },
    "case-d-vendor-review": {
        "label_ja": "取引先確認",
        "expected_recommendation": "REFER_VENDOR_REVIEW",
        "business_value_ja": "支払先口座が取引先マスタと一致しないケースです。",
    },
    "case-e-grn-mismatch": {
        "label_ja": "検収差異",
        "expected_recommendation": "REFER_GRN_MISMATCH",
        "business_value_ja": "検収数量不足を検出し、未検収支払を防ぐケースです。",
    },
    "case-f-tax-review": {
        "label_ja": "税務確認",
        "expected_recommendation": "REFER_TAX_REVIEW",
        "business_value_ja": "税額差異を検出し、税務確認へ回すケースです。",
    },
}

SHORT_ALIASES: dict[str, list[str]] = {
    "case-a-pay-ready": ["case-a", "a"],
    "case-b-po-mismatch": ["case-b", "b"],
    "case-c-duplicate": ["case-c", "c"],
    "case-d-vendor-review": ["case-d", "d"],
    "case-e-grn-mismatch": ["case-e", "e"],
    "case-f-tax-review": ["case-f", "f"],
}

NEXT_ACTIONS_JA: dict[Recommendation, list[str]] = {
    Recommendation.PAY_READY_CANDIDATE: [
        "人間承認者が支払候補として最終確認してください。",
        "ERP/SaaSにはdraft payloadとして登録候補を確認してください。",
    ],
    Recommendation.REFER_PO_MISMATCH: [
        "購買担当にPO変更有無を確認してください。",
        "変更POがある場合は承認済みPOを追加してください。",
        "変更がない場合は請求書差戻し候補として扱ってください。",
    ],
    Recommendation.REFER_GRN_MISMATCH: [
        "納品・検収担当に受領状況と数量を確認してください。",
        "未検収の場合は支払保留にしてください。",
    ],
    Recommendation.REFER_VENDOR_REVIEW: [
        "取引先マスタの支払先口座と請求書記載口座を照合してください。",
        "支払先確認が完了するまで支払保留を推奨します。",
    ],
    Recommendation.REFER_DUPLICATE_REVIEW: [
        "過去請求が支払済みか確認してください。",
        "今回請求が再発行または訂正請求か確認してください。",
        "二重払いの可能性がなくなるまで支払保留にしてください。",
    ],
    Recommendation.REFER_TAX_REVIEW: [
        "税区分と税額計算を経理または税務担当に確認してください。",
        "税額差異が解消するまで支払保留にしてください。",
    ],
    Recommendation.REFER_INFO_REQUEST: [
        "不足している請求情報を依頼してください。",
        "必須情報が揃ってから再レビューしてください。",
    ],
    Recommendation.BLOCKED_CANDIDATE: [
        "ブロック対象取引先のため支払登録に進めないでください。",
        "管理者または購買責任者へエスカレーションしてください。",
    ],
}

APPROVAL_ACTIONS: dict[Recommendation, str] = {
    Recommendation.PAY_READY_CANDIDATE: "approve_candidate",
    Recommendation.REFER_PO_MISMATCH: "hold",
    Recommendation.REFER_GRN_MISMATCH: "hold",
    Recommendation.REFER_VENDOR_REVIEW: "hold",
    Recommendation.REFER_DUPLICATE_REVIEW: "hold",
    Recommendation.REFER_TAX_REVIEW: "hold",
    Recommendation.REFER_INFO_REQUEST: "hold",
    Recommendation.BLOCKED_CANDIDATE: "return_to_requester",
}


@dataclass
class UploadedDocument:
    document_id: str
    document_type: str
    file_path: Path
    sha256: str


@dataclass
class ReviewCase:
    case_id: str
    tenant_id: str
    workflow_pack: str
    ruleset_version: str
    case_label: str
    documents: dict[str, UploadedDocument] = field(default_factory=dict)
    result: DecisionResult | None = None
    completed_job_id: str | None = None


@dataclass
class ReviewJob:
    job_id: str
    case_id: str
    status: str
    result: DecisionResult | None = None
    error: str | None = None


class ReviewService:
    def __init__(
        self,
        *,
        project_root: str | Path | None = None,
        artifact_root: str | Path | None = None,
        default_workspace_dir: str | Path | None = None,
    ) -> None:
        self.project_root = Path(project_root or Path.cwd()).resolve()
        self.pack_dir = self.project_root / "workflow-packs" / WORKFLOW_PACK
        self.artifact_root = Path(artifact_root or self.project_root / "artifacts").resolve()
        self.default_workspace_dir = Path(
            default_workspace_dir or default_visible_workspace()
        ).resolve()
        self.allowed_upload_roots = [
            (self.project_root / "samples").resolve(),
            (self.pack_dir / "samples").resolve(),
            self.default_workspace_dir.resolve(),
        ]
        self._cases: dict[str, ReviewCase] = {}
        self._jobs: dict[str, ReviewJob] = {}

    def create_case(
        self,
        *,
        tenant_id: str,
        workflow_pack: str = WORKFLOW_PACK,
        ruleset_version: str = RULESET_VERSION,
        case_label: str = "",
    ) -> dict[str, Any]:
        if workflow_pack != WORKFLOW_PACK:
            raise ValueError(f"Unsupported workflow_pack: {workflow_pack}")
        if ruleset_version != RULESET_VERSION:
            raise ValueError(f"Unsupported ruleset_version: {ruleset_version}")
        case_id = f"AP-CASE-{uuid.uuid4().hex[:12].upper()}"
        self._cases[case_id] = ReviewCase(
            case_id=case_id,
            tenant_id=tenant_id,
            workflow_pack=workflow_pack,
            ruleset_version=ruleset_version,
            case_label=case_label,
        )
        return {
            "case_id": case_id,
            "upload_slots": [
                {"document_type": document_type, "required": True}
                for document_type in DOCUMENT_TYPES
            ],
            "write_policy": {
                "external_write_allowed": False,
                "draft_payload_allowed": True,
            },
        }

    def upload_document(self, *, case_id: str, document_type: str, file_path: str) -> dict[str, Any]:
        case = self._require_case(case_id)
        if case.result is not None:
            raise ValueError(f"Case {case_id} is already completed; documents cannot be modified.")
        if document_type not in DOCUMENT_TYPES:
            raise ValueError(f"Unsupported document_type: {document_type}")
        path = self._resolve_user_path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"Document not found: {file_path}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        document = UploadedDocument(
            document_id=f"doc-{document_type}-{len(case.documents) + 1:03d}",
            document_type=document_type,
            file_path=path,
            sha256=digest,
        )
        case.documents[document_type] = document
        return {
            "document_id": document.document_id,
            "case_id": case_id,
            "document_type": document_type,
            "status": "uploaded",
            "sha256": digest,
        }

    def start_review(self, *, case_id: str) -> dict[str, Any]:
        case = self._require_case(case_id)
        if case.result is not None and case.completed_job_id is not None:
            return {"job_id": case.completed_job_id, "case_id": case_id, "status": "completed"}
        missing = [document_type for document_type in DOCUMENT_TYPES if document_type not in case.documents]
        if missing:
            raise ValueError(f"Missing required documents: {', '.join(missing)}")
        job_id = f"job-{uuid.uuid4().hex[:12]}"
        job = ReviewJob(job_id=job_id, case_id=case_id, status="running")
        self._jobs[job_id] = job
        try:
            facts = load_canonical_from_documents(
                invoice_pdf=case.documents["invoice"].file_path,
                purchase_order_pdf=case.documents["purchase_order"].file_path,
                goods_receipt_pdf=case.documents["goods_receipt"].file_path,
            )
            result = review_invoice_packet(
                case_id=case_id,
                tenant_id=case.tenant_id,
                facts=facts,
                pack_dir=self.pack_dir,
                artifact_dir=self.artifact_root / case_id,
            )
            case.result = result
            case.completed_job_id = job_id
            job.result = result
            job.status = "completed"
        except Exception as exc:
            job.status = "failed"
            job.error = str(exc)
            raise
        return {"job_id": job_id, "case_id": case_id, "status": job.status}

    def get_review_result(self, *, job_id: str) -> dict[str, Any]:
        job = self._require_job(job_id)
        if job.status != "completed" or job.result is None:
            return {"job_id": job_id, "case_id": job.case_id, "status": job.status, "error": job.error}
        return {"job_id": job_id, "status": job.status, "result": job.result.model_dump(mode="json")}

    def build_draft_payload(
        self,
        *,
        case_id: str,
        target_system: str,
        mode: str = "draft_only",
    ) -> dict[str, Any]:
        if mode != "draft_only":
            raise ValueError("Only mode='draft_only' is supported. External writes are disabled.")
        case = self._require_case(case_id)
        if case.result is None:
            raise ValueError("Review must be completed before building a draft payload.")
        payloads = case.result.draft_payloads.model_dump(mode="json")
        if target_system not in payloads:
            raise ValueError(f"Unsupported target_system: {target_system}")
        payload = payloads[target_system]
        if isinstance(payload, dict):
            payload["write_performed"] = False
        return {
            "case_id": case_id,
            "target_system": target_system,
            "mode": mode,
            "payload": payload,
            "write_performed": False,
        }

    def list_demo_cases(self) -> dict[str, Any]:
        workspace_dir = self.default_workspace_dir.resolve()
        return {
            "demo_cases": [
                self._demo_case_descriptor(case_id, workspace_dir)
                for case_id in DEMO_CASES
            ],
            "usage_ja": "case_idを選び、review_ap_demo_caseで同梱サンプルをレビューできます。",
            "workspace_dir": str(workspace_dir),
            "workspace_initialized": _workspace_initialized(workspace_dir),
            "write_performed": False,
        }

    def create_ocr_smoke_test(self) -> dict[str, Any]:
        return build_ocr_smoke_test(self.default_workspace_dir.resolve())

    def submit_ocr_smoke_test_result(
        self,
        *,
        run_id: str,
        ocr_result: dict[str, Any],
    ) -> dict[str, Any]:
        return submit_ocr_smoke_test_result(
            workspace_dir=self.default_workspace_dir.resolve(),
            run_id=run_id,
            ocr_result=ocr_result,
        )

    def setup_demo_workspace(
        self,
        *,
        workspace_dir: str | None = None,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        workspace = self._resolve_workspace_dir(workspace_dir)
        source_root = self.project_root / "samples"
        if not source_root.is_dir():
            raise FileNotFoundError(f"Bundled samples not found: {source_root}")
        workspace.mkdir(parents=True, exist_ok=True)
        for case_id in DEMO_CASES:
            source = source_root / case_id
            target = workspace / case_id
            if target.exists():
                if overwrite:
                    shutil.rmtree(target)
                else:
                    continue
            shutil.copytree(source, target)
        self._remember_allowed_root(workspace)
        return {
            "workspace_dir": str(workspace),
            "cases": [self._workspace_case_descriptor(case_id, workspace) for case_id in DEMO_CASES],
            "usage_ja": (
                "PDFを開いて確認できます。レビューする場合は『case-aをレビューして』"
                "またはフォルダパスを指定してください。"
            ),
            "write_performed": False,
        }

    def list_demo_cases_with_workspace(self) -> dict[str, Any]:
        workspace = self.default_workspace_dir.resolve()
        self._remember_allowed_root(workspace)
        return {
            "workspace_dir": str(workspace),
            "workspace_initialized": _workspace_initialized(workspace),
            "demo_cases": [self._demo_case_descriptor(case_id, workspace) for case_id in DEMO_CASES],
            "write_performed": False,
        }

    def review_demo_case(
        self,
        *,
        case_id: str,
        tenant_id: str = "demo-tenant",
        target_system: str = "generic_ap",
    ) -> dict[str, Any]:
        normalized_case_id = _normalize_demo_case_id(case_id)
        if normalized_case_id not in DEMO_CASES:
            raise ValueError(f"Unknown demo case: {case_id}")
        workspace = self.default_workspace_dir.resolve()
        case_dir = workspace / normalized_case_id
        if not case_dir.is_dir():
            self.setup_demo_workspace()
        case_dir = workspace / normalized_case_id
        return self.review_folder(
            tenant_id=tenant_id,
            folder_path=str(case_dir),
            target_system=target_system,
            demo_case_id=normalized_case_id,
        )

    def preview_folder(self, *, folder_path: str) -> dict[str, Any]:
        folder = self._resolve_folder_path(folder_path)
        return self._preview_folder(folder)

    def review_folder(
        self,
        *,
        folder_path: str,
        tenant_id: str = "demo-tenant",
        target_system: str = "generic_ap",
        demo_case_id: str | None = None,
    ) -> dict[str, Any]:
        folder = self._resolve_folder_path(folder_path)
        preview = self._preview_folder(folder)
        if not preview["ready_for_review"]:
            return {**preview, "status": "blocked", "write_performed": False}
        docs_by_type = {
            str(item["document_type"]): str(item["path"]) for item in preview["detected_documents"]
        }
        result = self.review_invoice_packet_from_paths(
            tenant_id=tenant_id,
            invoice_path=docs_by_type["invoice"],
            purchase_order_path=docs_by_type["purchase_order"],
            goods_receipt_path=docs_by_type["goods_receipt"],
            case_label=folder.name,
            target_system=target_system,
            demo_case_id=demo_case_id,
        )
        return {
            "folder_path": str(folder),
            "detected_documents": preview["detected_documents"],
            **result,
        }

    def review_invoice_packet_from_paths(
        self,
        *,
        tenant_id: str,
        invoice_path: str,
        purchase_order_path: str,
        goods_receipt_path: str,
        case_label: str = "",
        target_system: str = "generic_ap",
        demo_case_id: str | None = None,
    ) -> dict[str, Any]:
        if target_system not in TARGET_SYSTEMS:
            raise ValueError(f"Unsupported target_system: {target_system}")
        created = self.create_case(tenant_id=tenant_id, case_label=case_label)
        case_id = str(created["case_id"])
        uploads = [
            self.upload_document(
                case_id=case_id,
                document_type="invoice",
                file_path=invoice_path,
            ),
            self.upload_document(
                case_id=case_id,
                document_type="purchase_order",
                file_path=purchase_order_path,
            ),
            self.upload_document(
                case_id=case_id,
                document_type="goods_receipt",
                file_path=goods_receipt_path,
            ),
        ]
        started = self.start_review(case_id=case_id)
        job_id = str(started["job_id"])
        result = self._require_job(job_id).result
        if result is None:
            raise RuntimeError(f"Review did not complete for job_id: {job_id}")
        draft = self.build_draft_payload(case_id=case_id, target_system=target_system)
        return _business_packet(
            result=result,
            job_id=job_id,
            demo_case_id=demo_case_id,
            target_system=target_system,
            draft_payload=draft["payload"],
            uploads=uploads,
        )

    def explain_exception(self, *, job_id: str, audience: str = "ap_operator") -> dict[str, Any]:
        if audience not in AUDIENCES:
            raise ValueError(f"Unsupported audience: {audience}")
        job = self._require_job(job_id)
        if job.result is None:
            raise ValueError(f"Review result is not available for job_id: {job_id}")
        result = job.result
        return {
            "job_id": job_id,
            "case_id": result.case_id,
            "audience": audience,
            "recommendation": result.recommendation.value,
            "recommendation_label_ja": result.recommendation_label_ja,
            "exception_summary_ja": _exception_summary_ja(result),
            "root_causes": [_root_cause(rule) for rule in result.rule_results],
            "rule_ids": [rule.rule_id for rule in result.rule_results],
            "evidence": [_evidence_summary(evidence) for evidence in result.evidence],
            "next_actions_ja": NEXT_ACTIONS_JA[result.recommendation],
            "draft_message_ja": _draft_message_ja(result, audience),
            "write_performed": False,
        }

    def build_approval_brief(self, *, job_id: str) -> dict[str, Any]:
        job = self._require_job(job_id)
        if job.result is None:
            raise ValueError(f"Review result is not available for job_id: {job_id}")
        result = job.result
        action = APPROVAL_ACTIONS[result.recommendation]
        return {
            "job_id": job_id,
            "case_id": result.case_id,
            "approval_recommendation": action,
            "recommendation": result.recommendation.value,
            "recommendation_label_ja": result.recommendation_label_ja,
            "brief_ja": _approval_brief_ja(result, action),
            "risk_points_ja": _risk_points_ja(result),
            "evidence": [_evidence_summary(evidence) for evidence in result.evidence],
            "rule_ids": [rule.rule_id for rule in result.rule_results],
            "next_actions_ja": NEXT_ACTIONS_JA[result.recommendation],
            "write_performed": False,
        }

    def _require_case(self, case_id: str) -> ReviewCase:
        try:
            return self._cases[case_id]
        except KeyError as exc:
            raise KeyError(f"Unknown case_id: {case_id}") from exc

    def _require_job(self, job_id: str) -> ReviewJob:
        try:
            return self._jobs[job_id]
        except KeyError as exc:
            raise KeyError(f"Unknown job_id: {job_id}") from exc

    def _resolve_user_path(self, file_path: str) -> Path:
        path = Path(file_path).expanduser()
        if not path.is_absolute():
            path = self.project_root / path
        resolved = path.resolve()
        if resolved.suffix.lower() != ".pdf":
            raise PermissionError("Only .pdf demo documents can be uploaded.")
        if not any(_is_relative_to(resolved, root) for root in self.allowed_upload_roots):
            allowed = ", ".join(str(root) for root in self.allowed_upload_roots)
            raise PermissionError(f"File path must stay within demo sample directories: {allowed}")
        return resolved

    def _resolve_workspace_dir(self, workspace_dir: str | None) -> Path:
        if workspace_dir is None or str(workspace_dir).strip() == "":
            workspace = self.default_workspace_dir
        else:
            workspace = Path(workspace_dir).expanduser()
            if not workspace.is_absolute():
                workspace = self.project_root / workspace
        resolved = workspace.resolve()
        documents_root = (Path.home() / "Documents").resolve()
        if not (
            _is_relative_to(resolved, documents_root)
            or _is_relative_to(resolved, self.project_root)
        ):
            raise PermissionError(
                "Demo workspace must be under the user's Documents directory or this project."
            )
        self._remember_allowed_root(resolved)
        return resolved

    def _resolve_folder_path(self, folder_path: str) -> Path:
        folder = Path(folder_path).expanduser()
        if not folder.is_absolute():
            folder = self.project_root / folder
        resolved = folder.resolve()
        if not any(_is_relative_to(resolved, root) for root in self.allowed_upload_roots):
            allowed = ", ".join(str(root) for root in self.allowed_upload_roots)
            raise PermissionError(f"Folder path must stay within demo workspace directories: {allowed}")
        if not resolved.is_dir():
            raise FileNotFoundError(f"Folder not found: {folder_path}")
        return resolved

    def _remember_allowed_root(self, root: Path) -> None:
        resolved = root.resolve()
        if not any(existing == resolved for existing in self.allowed_upload_roots):
            self.allowed_upload_roots.append(resolved)

    def _preview_folder(self, folder: Path) -> dict[str, Any]:
        pdfs = sorted(folder.glob("*.pdf"))
        if not pdfs:
            return _folder_error(
                folder=folder,
                error_code="NO_PDF_DOCUMENTS",
                message_ja="フォルダ内にPDFが見つかりません。",
            )
        classified: dict[str, dict[str, Any]] = {}
        unclassified: list[str] = []
        errors: list[str] = []
        for pdf in pdfs:
            sidecar = pdf.with_suffix(".json")
            sidecar_type = None
            fields: dict[str, Any] = {}
            if sidecar.exists():
                payload = json.loads(sidecar.read_text("utf-8"))
                sidecar_type = payload.get("document_type")
                fields = payload.get("fields", {})
            filename_type = _classify_by_filename(pdf.name)
            document_type = sidecar_type or filename_type
            if document_type and document_type not in DOCUMENT_TYPES:
                errors.append(f"{pdf.name}: unsupported document_type {document_type}")
                continue
            if sidecar_type and filename_type and sidecar_type != filename_type:
                errors.append(
                    f"{pdf.name}: sidecar document_type {sidecar_type} conflicts with filename"
                )
                continue
            if not document_type:
                unclassified.append(pdf.name)
                continue
            if not sidecar.exists():
                errors.append(f"{pdf.name}: missing sidecar JSON")
                continue
            if document_type in classified:
                errors.append(f"{pdf.name}: duplicate {document_type} document")
                continue
            classified[document_type] = {
                "document_type": document_type,
                "path": str(pdf),
                "sidecar_path": str(sidecar),
                "key_fields": _key_fields(document_type, fields),
            }
        missing = [document_type for document_type in DOCUMENT_TYPES if document_type not in classified]
        if unclassified:
            return _folder_error(
                folder=folder,
                error_code="DOCUMENT_CLASSIFICATION_REQUIRED",
                message_ja="フォルダ内に分類できないPDFがあります。どの帳票種別か確認してください。",
                unclassified_files=unclassified,
                detected_documents=classified,
            )
        if errors:
            return _folder_error(
                folder=folder,
                error_code="DOCUMENT_VALIDATION_FAILED",
                message_ja="フォルダ内の帳票またはsidecar JSONを確認してください。",
                validation_errors=errors,
                detected_documents=classified,
            )
        if missing:
            return _folder_error(
                folder=folder,
                error_code="REQUIRED_DOCUMENTS_MISSING",
                message_ja="レビューに必要な帳票が不足しています。",
                missing_document_types=missing,
                detected_documents=classified,
            )
        return {
            "folder_path": str(folder),
            "detected_documents": [classified[document_type] for document_type in DOCUMENT_TYPES],
            "ready_for_review": True,
            "write_performed": False,
        }

    def _workspace_case_descriptor(self, case_id: str, workspace: Path) -> dict[str, Any]:
        case_dir = workspace / case_id
        return {
            "case_id": case_id,
            "case_dir": str(case_dir),
            "documents": [
                {
                    "document_type": document_type,
                    "path": str(case_dir / f"{document_type}.pdf"),
                }
                for document_type in DOCUMENT_TYPES
            ],
        }

    def _demo_case_descriptor(self, case_id: str, workspace: Path) -> dict[str, Any]:
        metadata = DEMO_CASES[case_id]
        case_dir = workspace / case_id
        return {
            "case_id": case_id,
            "short_aliases": SHORT_ALIASES[case_id],
            **metadata,
            "case_dir": str(case_dir),
            "documents": ["invoice.pdf", "purchase_order.pdf", "goods_receipt.pdf"],
        }


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _normalize_demo_case_id(case_id: str) -> str:
    aliases = {
        "case-a": "case-a-pay-ready",
        "a": "case-a-pay-ready",
        "case-b": "case-b-po-mismatch",
        "b": "case-b-po-mismatch",
        "case-c": "case-c-duplicate",
        "c": "case-c-duplicate",
        "case-d": "case-d-vendor-review",
        "d": "case-d-vendor-review",
        "case-e": "case-e-grn-mismatch",
        "e": "case-e-grn-mismatch",
        "case-f": "case-f-tax-review",
        "f": "case-f-tax-review",
    }
    return aliases.get(case_id.strip().lower(), case_id.strip())


def _workspace_initialized(workspace: Path) -> bool:
    return all((workspace / case_id).is_dir() for case_id in DEMO_CASES)


def _classify_by_filename(filename: str) -> str | None:
    name = filename.lower()
    stem = Path(name).stem
    if name in {"invoice.pdf", "請求書.pdf"}:
        return "invoice"
    if stem.startswith("invoice_") or stem.endswith("_invoice"):
        return "invoice"
    if name in {"purchase_order.pdf", "po.pdf", "発注書.pdf"}:
        return "purchase_order"
    if stem.startswith("po_") or stem.endswith("_po"):
        return "purchase_order"
    if name in {
        "goods_receipt.pdf",
        "grn.pdf",
        "receipt.pdf",
        "納品書.pdf",
        "検収書.pdf",
        "inspection_report.pdf",
    }:
        return "goods_receipt"
    if stem.startswith("grn_") or stem.endswith("_grn") or stem.endswith("_receipt"):
        return "goods_receipt"
    return None


def _key_fields(document_type: str, fields: dict[str, Any]) -> dict[str, Any]:
    if document_type == "invoice":
        return {
            "invoice_number": fields.get("invoice_number"),
            "vendor_id": fields.get("vendor_id"),
            "po_number": fields.get("po_number"),
            "total_amount": fields.get("total_amount"),
        }
    if document_type == "purchase_order":
        return {
            "po_number": fields.get("po_number"),
            "vendor_id": fields.get("vendor_id"),
            "total_amount": fields.get("total_amount"),
            "approved": fields.get("approved"),
        }
    return {
        "receipt_number": fields.get("receipt_number"),
        "po_number": fields.get("po_number"),
        "received": fields.get("received"),
        "received_quantity": fields.get("received_quantity"),
    }


def _folder_error(
    *,
    folder: Path,
    error_code: str,
    message_ja: str,
    detected_documents: dict[str, dict[str, Any]] | None = None,
    unclassified_files: list[str] | None = None,
    validation_errors: list[str] | None = None,
    missing_document_types: list[str] | None = None,
) -> dict[str, Any]:
    detected = detected_documents or {}
    return {
        "folder_path": str(folder),
        "ready_for_review": False,
        "error_code": error_code,
        "message_ja": message_ja,
        "unclassified_files": unclassified_files or [],
        "validation_errors": validation_errors or [],
        "missing_document_types": missing_document_types or [],
        "detected_documents": {
            document_type: detected.get(document_type) for document_type in DOCUMENT_TYPES
        },
        "allowed_document_types": list(DOCUMENT_TYPES),
        "write_performed": False,
    }


def _business_packet(
    *,
    result: DecisionResult,
    job_id: str,
    demo_case_id: str | None,
    target_system: str,
    draft_payload: dict[str, Any],
    uploads: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "case_id": result.case_id,
        "job_id": job_id,
        "demo_case_id": demo_case_id,
        "target_system": target_system,
        "recommendation": result.recommendation.value,
        "recommendation_label_ja": result.recommendation_label_ja,
        "business_meaning_ja": _business_meaning_ja(result.recommendation),
        "summary_ja": result.summary,
        "exception_summary_ja": _exception_summary_ja(result),
        "exceptions": result.exceptions,
        "rule_results": [rule.model_dump(mode="json") for rule in result.rule_results],
        "rule_ids": [rule.rule_id for rule in result.rule_results],
        "match_results": {
            key: value.model_dump(mode="json") for key, value in result.match_results.items()
        },
        "evidence": [_evidence_summary(evidence) for evidence in result.evidence],
        "missing_information": result.missing_information,
        "next_actions_ja": NEXT_ACTIONS_JA[result.recommendation],
        "draft_payload": draft_payload,
        "draft_payload_summary": _draft_payload_summary(draft_payload),
        "audit_artifacts": result.audit_artifacts.model_dump(mode="json"),
        "document_uploads": uploads,
        "demo_note": (
            "This demo requires sidecar JSON files next to the sample PDFs. "
            "Production OCR/Textract is out of scope for this MCPB demo."
        ),
        "write_performed": False,
    }


def _business_meaning_ja(recommendation: Recommendation) -> str:
    return {
        Recommendation.PAY_READY_CANDIDATE: "人間承認後の支払候補です。自動支払承認ではありません。",
        Recommendation.REFER_PO_MISMATCH: "PO金額・承認・残高・取引先などの確認が必要です。",
        Recommendation.REFER_GRN_MISMATCH: "納品または検収状況の確認が必要です。",
        Recommendation.REFER_VENDOR_REVIEW: "取引先マスタまたは支払先口座の確認が必要です。",
        Recommendation.REFER_DUPLICATE_REVIEW: "二重払い防止のため過去請求との照合確認が必要です。",
        Recommendation.REFER_TAX_REVIEW: "税区分または税額計算の確認が必要です。",
        Recommendation.REFER_INFO_REQUEST: "レビューに必要な情報が不足しています。",
        Recommendation.BLOCKED_CANDIDATE: "支払ブロック候補であり差戻しまたは管理者確認が必要です。",
    }[recommendation]


def _exception_summary_ja(result: DecisionResult) -> str:
    if not result.rule_results:
        return "主要照合項目に例外はありません。"
    return " / ".join(f"{rule.rule_id}: {rule.description}" for rule in result.rule_results)


def _root_cause(rule: RuleResult) -> dict[str, Any]:
    return {
        "rule_id": rule.rule_id,
        "recommendation": rule.recommendation.value,
        "reason_ja": _rule_reason_ja(rule),
        "evidence": [_evidence_summary(evidence) for evidence in rule.evidence],
    }


def _rule_reason_ja(rule: RuleResult) -> str:
    return {
        "AP-REQ-001": "請求書番号など必須項目が不足しています。",
        "AP-VENDOR-001": "取引先がマスタに存在しません。",
        "AP-VENDOR-002": "請求書上の銀行口座が取引先マスタと一致しません。",
        "AP-PO-001": "請求内容がPO条件または許容差と一致しません。",
        "AP-GRN-001": "検収・納品情報が請求内容を満たしていません。",
        "AP-DUP-001": "過去請求と重複する可能性があります。",
        "AP-TAX-001": "税額または税区分に差異があります。",
        "AP-BLOCK-001": "取引先が支払ブロック対象です。",
    }.get(rule.rule_id, rule.description)


def _evidence_summary(evidence: Evidence) -> dict[str, Any]:
    return {
        "document_type": evidence.document_type,
        "document_name": evidence.document_name,
        "page": evidence.page,
        "field_label": evidence.field_label,
        "normalized_value": evidence.normalized_value,
    }


def _draft_payload_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "vendor_id": payload.get("vendor_id") or payload.get("partner_code"),
        "invoice_number": payload.get("invoice_number"),
        "total_amount": payload.get("total_amount") or payload.get("amount"),
        "payment_status": payload.get("payment_status", "draft"),
        "write_performed": False,
    }


def _draft_message_ja(result: DecisionResult, audience: str) -> str:
    base = "draft payloadは生成済みですが、外部ERP/SaaSへの本書き込みは行っていません。"
    if audience == "vendor_contact":
        return f"{base} 取引先へは差異解消に必要な事項のみを依頼してください。"
    if result.recommendation is Recommendation.PAY_READY_CANDIDATE:
        return f"{base} 人間承認後の登録候補として扱ってください。"
    return f"{base} 例外が解消するまで支払登録は保留してください。"


def _approval_brief_ja(result: DecisionResult, action: str) -> str:
    return (
        f"判定: {result.recommendation.value}\n"
        f"支払判断: {action}\n"
        f"理由: {_exception_summary_ja(result)}\n"
        f"write_performed=false"
    )


def _risk_points_ja(result: DecisionResult) -> list[str]:
    if result.recommendation is Recommendation.PAY_READY_CANDIDATE:
        return ["主要照合項目は一致していますが、人間承認前の自動支払は行いません。"]
    return [f"{rule.rule_id}: {_rule_reason_ja(rule)}" for rule in result.rule_results]
