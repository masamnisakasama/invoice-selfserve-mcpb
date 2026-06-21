from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .engine import RULESET_VERSION, WORKFLOW_PACK, review_invoice_packet
from .extraction import load_canonical_from_documents
from .models import DecisionResult


DOCUMENT_TYPES = ("invoice", "purchase_order", "goods_receipt")


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
    ) -> None:
        self.project_root = Path(project_root or Path.cwd()).resolve()
        self.pack_dir = self.project_root / "workflow-packs" / WORKFLOW_PACK
        self.artifact_root = Path(artifact_root or self.project_root / "artifacts").resolve()
        self._cases: dict[str, ReviewCase] = {}
        self._jobs: dict[str, ReviewJob] = {}
        self._case_seq = 0
        self._job_seq = 0

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
        self._case_seq += 1
        case_id = f"AP-CASE-{self._case_seq:04d}"
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
        missing = [document_type for document_type in DOCUMENT_TYPES if document_type not in case.documents]
        if missing:
            raise ValueError(f"Missing required documents: {', '.join(missing)}")
        self._job_seq += 1
        job_id = f"job-{self._job_seq:04d}"
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
        return path.resolve()
