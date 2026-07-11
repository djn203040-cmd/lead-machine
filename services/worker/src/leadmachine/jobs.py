"""Worker run logging (M7 observability).

Every CLI run records itself in the ``jobs`` table so a non-dev can see, from
the dashboard, what ran, when, whether it succeeded, and the resulting stats —
without reading server logs. :class:`JobRun` is a context manager:

    with JobRun(db, "discover", search_id=sid) as job:
        stats = run_discovery(...)
        job.result = stats.as_dict()

It inserts a ``running`` row on enter, then flips it to ``done`` (with
``result``) or ``failed`` (with ``error``) on exit. Persistence failures are
swallowed — logging must never take down the actual job — and a ``None`` client
makes it a no-op so unit tests need no database.
"""

from __future__ import annotations

import traceback
from datetime import datetime, timezone
from types import TracebackType
from typing import Any

# CLI command name -> jobs.type CHECK value.
JOB_TYPES = {
    "discover": "discover",
    "qualify": "qualify_website",
    "enrich-financial": "enrich_financial",
    "score": "score",
    "angles": "angle",
    "find-phones": "find_phones",
    "screen": "robinson",
    "enrich-queued": "enrich_queued",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobRun:
    """Records a single worker run in the ``jobs`` table."""

    def __init__(
        self,
        client: Any | None,
        job_type: str,
        *,
        search_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.client = client
        self.job_type = JOB_TYPES.get(job_type, job_type)
        self.search_id = search_id
        self.payload = payload or {}
        self.result: dict[str, Any] | None = None
        self.job_id: str | None = None

    def __enter__(self) -> "JobRun":
        if self.client is None:
            return self
        try:
            row: dict[str, Any] = {
                "type": self.job_type,
                "status": "running",
                "payload": self.payload,
                "attempts": 1,
                "started_at": _now_iso(),
            }
            if self.search_id:
                row["search_id"] = self.search_id
            res = self.client.table("jobs").insert(row).execute()
            self.job_id = (res.data or [{}])[0].get("id")
        except Exception:
            self.job_id = None
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        if self.client is None or self.job_id is None:
            return False  # never suppress the exception
        update: dict[str, Any] = {"finished_at": _now_iso()}
        if exc is None:
            update["status"] = "done"
            update["result"] = self.result
        else:
            update["status"] = "failed"
            update["error"] = "".join(
                traceback.format_exception_only(exc_type, exc)
            ).strip()[:2000]
        try:
            self.client.table("jobs").update(update).eq("id", self.job_id).execute()
        except Exception:
            pass
        return False
