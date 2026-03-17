"""Audit event recording helpers."""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import AuditEvent


class AuditService:
    async def record(
        self,
        db: AsyncSession,
        action: str,
        actor: str,
        *,
        session_id: uuid.UUID | None = None,
        task_id: uuid.UUID | None = None,
        agent_id: uuid.UUID | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        event = AuditEvent(
            session_id=session_id,
            task_id=task_id,
            agent_id=agent_id,
            action=action,
            actor=actor,
            details=json.dumps(details) if details else None,
        )
        db.add(event)
