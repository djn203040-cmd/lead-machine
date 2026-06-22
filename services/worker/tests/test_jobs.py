"""Worker run logging into the ``jobs`` table (M7 observability)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from leadmachine.jobs import JOB_TYPES, JobRun


class FakeJobsTable:
    def __init__(self, store: list[dict[str, Any]]) -> None:
        self.store = store
        self._mode: str | None = None
        self._row: dict[str, Any] | None = None
        self._id: str | None = None

    def insert(self, row: dict[str, Any]) -> "FakeJobsTable":
        self._mode, self._row = "insert", dict(row)
        return self

    def update(self, row: dict[str, Any]) -> "FakeJobsTable":
        self._mode, self._row = "update", dict(row)
        return self

    def eq(self, _col: str, value: Any) -> "FakeJobsTable":
        self._id = value
        return self

    def execute(self) -> SimpleNamespace:
        if self._mode == "insert":
            assert self._row is not None
            self._row["id"] = f"job-{len(self.store) + 1}"
            self.store.append(self._row)
            return SimpleNamespace(data=[{"id": self._row["id"]}])
        # update: merge into the stored row by id
        for rec in self.store:
            if rec["id"] == self._id:
                rec.update(self._row or {})
        return SimpleNamespace(data=[])


class FakeJobsDb:
    def __init__(self) -> None:
        self.jobs: list[dict[str, Any]] = []

    def table(self, name: str) -> FakeJobsTable:
        assert name == "jobs"
        return FakeJobsTable(self.jobs)


def test_cli_name_maps_to_check_constraint_type() -> None:
    assert JOB_TYPES["qualify"] == "qualify_website"
    assert JOB_TYPES["angles"] == "angle"
    assert JOB_TYPES["screen"] == "robinson"


def test_success_records_done_with_result() -> None:
    db = FakeJobsDb()
    with JobRun(db, "discover", search_id="s1") as job:
        job.result = {"seen": 5, "upserted": 3}

    assert len(db.jobs) == 1
    rec = db.jobs[0]
    assert rec["type"] == "discover"
    assert rec["search_id"] == "s1"
    assert rec["status"] == "done"
    assert rec["result"] == {"seen": 5, "upserted": 3}
    assert rec["started_at"] and rec["finished_at"]


def test_failure_records_failed_with_error_and_reraises() -> None:
    db = FakeJobsDb()
    with pytest.raises(ValueError):
        with JobRun(db, "score"):
            raise ValueError("boom")

    rec = db.jobs[0]
    assert rec["status"] == "failed"
    assert "boom" in rec["error"]
    assert rec["type"] == "score"


def test_none_client_is_a_noop() -> None:
    with JobRun(None, "qualify") as job:
        job.result = {"ok": True}
    # nothing to assert beyond "did not raise"


def test_insert_failure_does_not_break_the_job() -> None:
    class ExplodingDb:
        def table(self, _name: str) -> Any:
            raise RuntimeError("db down")

    # Logging must never take down the real work.
    with JobRun(ExplodingDb(), "angles") as job:
        job.result = {"generated": 1}
