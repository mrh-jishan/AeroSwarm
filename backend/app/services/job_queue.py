"""Durable background job queue backed by PostgreSQL."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.base import BackgroundJob

JOB_TYPE_SESSION_BOOTSTRAP = "session_bootstrap"
JOB_TYPE_MERGE_PREFLIGHT = "merge_preflight"


@dataclass(slots=True)
class ClaimedJob:
    id: uuid.UUID
    job_type: str
    payload: dict[str, Any]
    session_id: uuid.UUID | None
    merge_request_id: uuid.UUID | None
    attempts: int


class JobQueueService:
    async def enqueue(
        self,
        db: AsyncSession,
        *,
        job_type: str,
        payload: dict[str, Any] | None = None,
        session_id: uuid.UUID | None = None,
        merge_request_id: uuid.UUID | None = None,
        max_attempts: int | None = None,
    ) -> BackgroundJob:
        job = BackgroundJob(
            job_type=job_type,
            status="queued",
            session_id=session_id,
            merge_request_id=merge_request_id,
            payload=json.dumps(payload) if payload else None,
            attempts=0,
            max_attempts=max_attempts or settings.JOB_MAX_ATTEMPTS,
            available_at=datetime.now(timezone.utc),
        )
        db.add(job)
        await db.flush()
        return job

    async def claim_next(self, db: AsyncSession, *, worker_id: str) -> ClaimedJob | None:
        now = datetime.now(timezone.utc)
        stale_before = now - timedelta(seconds=settings.JOB_LOCK_TIMEOUT_SECONDS)

        result = await db.execute(
            select(BackgroundJob)
            .where(
                or_(
                    BackgroundJob.status == "queued",
                    (
                        (BackgroundJob.status == "running")
                        & (BackgroundJob.locked_at.is_not(None))
                        & (BackgroundJob.locked_at < stale_before)
                    ),
                ),
                BackgroundJob.available_at <= now,
            )
            .order_by(BackgroundJob.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        job = result.scalar_one_or_none()
        if job is None:
            return None

        job.status = "running"
        job.locked_by = worker_id
        job.locked_at = now
        job.attempts += 1
        job.error_message = None
        await db.commit()
        await db.refresh(job)

        return ClaimedJob(
            id=job.id,
            job_type=job.job_type,
            payload=json.loads(job.payload) if job.payload else {},
            session_id=job.session_id,
            merge_request_id=job.merge_request_id,
            attempts=job.attempts,
        )

    async def complete(
        self,
        db: AsyncSession,
        *,
        job_id: uuid.UUID,
        result_payload: dict[str, Any] | None = None,
    ) -> None:
        job = await db.get(BackgroundJob, job_id)
        if job is None:
            return
        job.status = "succeeded"
        job.result = json.dumps(result_payload) if result_payload else None
        job.error_message = None
        job.locked_at = None
        job.locked_by = None
        job.available_at = datetime.now(timezone.utc)
        await db.commit()

    async def fail(
        self,
        db: AsyncSession,
        *,
        job_id: uuid.UUID,
        error_message: str,
    ) -> None:
        job = await db.get(BackgroundJob, job_id)
        if job is None:
            return

        job.error_message = error_message
        job.locked_at = None
        job.locked_by = None

        if job.attempts < job.max_attempts:
            retry_delay = settings.JOB_RETRY_BASE_SECONDS * job.attempts
            job.status = "queued"
            job.available_at = datetime.now(timezone.utc) + timedelta(seconds=retry_delay)
        else:
            job.status = "failed"
            job.available_at = datetime.now(timezone.utc)

        await db.commit()
