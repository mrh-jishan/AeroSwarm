"""Background job worker process."""

from __future__ import annotations

import asyncio
import os
import socket
import uuid

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.services.job_queue import (
    JOB_TYPE_MERGE_PREFLIGHT,
    JOB_TYPE_SESSION_BOOTSTRAP,
    ClaimedJob,
    JobQueueService,
)
from app.services.merge_preflight import MergePreflightService
from app.services.session_bootstrap import SessionBootstrapService


class BackgroundWorker:
    def __init__(self) -> None:
        self._queue = JobQueueService()
        self._session_bootstrap = SessionBootstrapService()
        self._merge_preflight = MergePreflightService()
        self._worker_id = f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4()}"

    async def run_forever(self) -> None:
        while True:
            claimed = await self._claim_next()
            if claimed is None:
                await asyncio.sleep(settings.JOB_POLL_INTERVAL_SECONDS)
                continue
            await self._process_job(claimed)

    async def _claim_next(self) -> ClaimedJob | None:
        async with AsyncSessionLocal() as db:
            return await self._queue.claim_next(db, worker_id=self._worker_id)

    async def _process_job(self, claimed: ClaimedJob) -> None:
        try:
            async with AsyncSessionLocal() as db:
                if claimed.job_type == JOB_TYPE_SESSION_BOOTSTRAP:
                    if claimed.session_id is None:
                        raise ValueError("Session bootstrap job is missing session_id")
                    result = await self._session_bootstrap.run(
                        db,
                        session_id=claimed.session_id,
                        actor=str(claimed.payload.get("requested_by", "system")),
                        payload=claimed.payload,
                    )
                elif claimed.job_type == JOB_TYPE_MERGE_PREFLIGHT:
                    if claimed.merge_request_id is None:
                        raise ValueError("Merge preflight job is missing merge_request_id")
                    result = await self._merge_preflight.run(
                        db,
                        merge_request_id=claimed.merge_request_id,
                        actor=str(claimed.payload.get("requested_by", "system")),
                    )
                else:
                    raise ValueError(f"Unsupported job type: {claimed.job_type}")

            async with AsyncSessionLocal() as db:
                await self._queue.complete(db, job_id=claimed.id, result_payload=result)
        except Exception as exc:
            async with AsyncSessionLocal() as db:
                await self._queue.fail(db, job_id=claimed.id, error_message=str(exc))


async def main() -> None:
    worker = BackgroundWorker()
    await worker.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
