"""Asynchronous model-neutral exports and the delete-user privacy cascade."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.errors import forbidden, not_found
from app.auth import TenantContext
from app.config import get_settings
from app.db.session import session_scope
from app.hms import HmsClient, HmsError
from app.models.enums import AuditAction, ExportStatus, MemoryStatus, PassportStatus
from app.models.export import ExportJob
from app.models.identity import User
from app.models.memory import MemoryRecord
from app.models.memory_mapping import MemoryRecordHmsUnit
from app.schemas.data_ops import DeleteUserResponse, ExportStatusResponse
from app.services.audit import api_actor, write_audit
from app.services.ids import new_export_id

_EXPORT_TOKENS: dict[str, str] = {}


def _now() -> datetime:
    return datetime.now(tz=UTC)


def create_export_job(
    db: Session,
    context: TenantContext,
    user_id: str,
) -> ExportJob:
    user = _authorized_user(db, context.tenant.id, user_id)
    if user.passport_status == PassportStatus.DELETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="cannot export a deleted passport",
        )
    settings = get_settings()
    token = secrets.token_urlsafe(32)
    job = ExportJob(
        id=new_export_id(),
        tenant_id=context.tenant.id,
        user_id=user.id,
        requested_by=api_actor(context.api_key.id),
        status=ExportStatus.PENDING,
        download_token_hash=_token_hash(token),
        download_token_expires_at=_now()
        + timedelta(seconds=settings.export_token_ttl_seconds),
        artifact_path=None,
        error_message=None,
        created_at=_now(),
        completed_at=None,
    )
    db.add(job)
    db.flush()
    _EXPORT_TOKENS[job.id] = token
    return job


def run_export_job(export_id: str) -> None:
    """Run after the request commits, using a fresh database session."""
    try:
        with session_scope() as db:
            job = db.get(ExportJob, export_id)
            if job is None or job.status != ExportStatus.PENDING:
                return
            user = db.get(User, job.user_id)
            if user is None:
                raise RuntimeError("export user disappeared")
            records = list(
                db.scalars(
                    select(MemoryRecord)
                    .where(
                        MemoryRecord.tenant_id == job.tenant_id,
                        MemoryRecord.user_id == job.user_id,
                    )
                    .order_by(MemoryRecord.id)
                )
            )
            now = _now()
            bundle = {
                "format": "memory-passport/v1",
                "exported_at": now.isoformat(),
                "user": {"id": user.id, "passport_id": user.passport_id},
                "memories": [_serialize_memory(record) for record in records],
            }
            artifact = _write_export_bundle(job.id, bundle)
            job.artifact_path = str(artifact)
            job.status = ExportStatus.COMPLETED
            job.completed_at = now
            job.error_message = None
            write_audit(
                db,
                tenant_id=job.tenant_id,
                actor=job.requested_by,
                action=AuditAction.MEMORY_EXPORTED,
                target=job.user_id,
                detail=f"Exported {len(records)} memories as memory-passport/v1",
            )
    except Exception:  # noqa: BLE001 - persist a sanitized failure state
        with session_scope() as db:
            job = db.get(ExportJob, export_id)
            if job is not None:
                job.status = ExportStatus.FAILED
                job.error_message = "export failed"
                job.completed_at = _now()
                job.artifact_path = None


def get_export_status(
    db: Session,
    tenant_id: str,
    export_id: str,
) -> ExportStatusResponse:
    job = _authorized_export(db, tenant_id, export_id)
    token = _EXPORT_TOKENS.get(job.id)
    unexpired = _as_utc(job.download_token_expires_at) >= _now()
    download_url = None
    if job.status == ExportStatus.COMPLETED and token and unexpired:
        download_url = f"/v1/exports/{job.id}/download?token={token}"
    return ExportStatusResponse(
        export_id=job.id,
        status=job.status,
        download_url=download_url,
        expires_at=(job.download_token_expires_at if download_url else None),
        error=(job.error_message if job.status == ExportStatus.FAILED else None),
    )


def resolve_export_download(
    db: Session,
    tenant_id: str,
    export_id: str,
    token: str,
) -> Path:
    job = _authorized_export(db, tenant_id, export_id)
    if job.status != ExportStatus.COMPLETED or not job.artifact_path:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="export is not ready")
    if _as_utc(job.download_token_expires_at) < _now():
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="download token expired")
    if not hmac.compare_digest(job.download_token_hash, _token_hash(token)):
        raise forbidden("invalid_export_token", "invalid export download token")
    export_root = Path(get_settings().export_dir).resolve()
    artifact = Path(job.artifact_path).resolve()
    if not artifact.is_relative_to(export_root) or not artifact.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="export artifact missing")
    return artifact


async def delete_user(
    db: Session,
    context: TenantContext,
    hms_client: HmsClient,
    user_id: str,
) -> DeleteUserResponse:
    user = _authorized_user(db, context.tenant.id, user_id)
    if user.passport_status == PassportStatus.DELETED:
        return DeleteUserResponse(
            user_id=user.id,
            tombstoned_memories=0,
            hms_bank_deleted=True,
            passport_status=user.passport_status,
        )
    try:
        await hms_client.delete_bank(user.id)
    except HmsError:
        db.rollback()
        raise

    records = list(
        db.scalars(
            select(MemoryRecord).where(
                MemoryRecord.tenant_id == context.tenant.id,
                MemoryRecord.user_id == user.id,
            )
        )
    )
    memory_ids = [record.id for record in records]
    for record in records:
        record.status = MemoryStatus.DELETED
    if memory_ids:
        db.execute(
            delete(MemoryRecordHmsUnit).where(
                MemoryRecordHmsUnit.tenant_id == context.tenant.id,
                MemoryRecordHmsUnit.mp_memory_id.in_(memory_ids),
            )
        )
    user.passport_status = PassportStatus.DELETED
    user.passport_deleted_at = _now()
    user.memory_enabled = False
    write_audit(
        db,
        tenant_id=context.tenant.id,
        actor=api_actor(context.api_key.id),
        action=AuditAction.USER_DELETED,
        target=user.id,
        detail=(
            f"Deleted passport and HMS bank; tombstoned {len(records)} memories"
        ),
    )
    return DeleteUserResponse(
        user_id=user.id,
        tombstoned_memories=len(records),
        hms_bank_deleted=True,
        passport_status=PassportStatus.DELETED,
    )


def _authorized_user(db: Session, tenant_id: str, user_id: str) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise not_found("User", user_id)
    if user.tenant_id != tenant_id:
        raise forbidden("cross_tenant_user", "user belongs to another tenant")
    return user


def _authorized_export(db: Session, tenant_id: str, export_id: str) -> ExportJob:
    job = db.get(ExportJob, export_id)
    if job is None:
        raise not_found("Export", export_id)
    if job.tenant_id != tenant_id:
        raise forbidden("cross_tenant_export", "export belongs to another tenant")
    return job


def _write_export_bundle(export_id: str, bundle: dict[str, Any]) -> Path:
    export_dir = Path(get_settings().export_dir)
    export_dir.mkdir(parents=True, exist_ok=True)
    final_path = export_dir / f"{export_id}.json"
    temp_path = export_dir / f".{export_id}.{secrets.token_hex(8)}.tmp"
    temp_path.write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    os.replace(temp_path, final_path)
    return final_path


def _serialize_memory(record: MemoryRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "passport_id": record.passport_id,
        "user_id": record.user_id,
        "relationship_id": record.relationship_id,
        "agent_id": record.agent_id,
        "device_id": record.device_id,
        "type": record.type.value,
        "content": record.content,
        "scope": record.scope.value,
        "sensitivity": record.sensitivity.value,
        "status": record.status.value,
        "confidence": record.confidence,
        "portability": record.portability,
        "source": record.source,
        "valid_from": record.valid_from.isoformat(),
        "expires_at": record.expires_at.isoformat() if record.expires_at else None,
        "version": record.version,
        "supersedes": record.supersedes,
    }


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


__all__ = [
    "create_export_job",
    "delete_user",
    "get_export_status",
    "resolve_export_download",
    "run_export_job",
]
