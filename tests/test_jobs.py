import time

import pytest

from app.errors import ServiceError
from app.jobs import Job, JobManager
from app.schemas import DocumentOptions


def test_queue_is_bounded_and_active_jobs_cannot_be_deleted(engine):
    engine.settings.queue_size = 1
    manager = JobManager(engine)
    try:
        with engine.gate:
            first = manager.submit(b"one@example.ru", "txt", DocumentOptions())
            # Wait for the worker to take the first item and block on the model gate.
            deadline = time.monotonic() + 5
            while manager.pending.qsize() and time.monotonic() < deadline:
                time.sleep(0.01)
            second = manager.submit(b"two@example.ru", "txt", DocumentOptions())
            with pytest.raises(ServiceError, match="document_queue_full"):
                manager.submit(b"three@example.ru", "txt", DocumentOptions())
            with pytest.raises(ServiceError, match="cannot_delete_active_job"):
                manager.delete(first["id"])
            assert manager.get(second["id"]).status == "queued"
    finally:
        manager.close()


def test_ttl_purges_finished_results_only(engine):
    manager = JobManager(engine)
    try:
        with manager.lock:
            manager.jobs["old"] = Job("old", status="succeeded", updated_at=0, output=b"clean")
            manager.jobs["active"] = Job("active", status="queued", updated_at=0)
        with pytest.raises(ServiceError, match="job_not_found_or_expired"):
            manager.get("old")
        assert manager.get("active").status == "queued"
    finally:
        manager.close()
