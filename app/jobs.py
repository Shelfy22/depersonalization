import queue
import threading
import time
import uuid
from dataclasses import dataclass, field

from app.documents import process_document
from app.engine import DetectionEngine
from app.errors import ServiceError
from app.schemas import DocumentOptions


@dataclass
class Job:
    id: str
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    status: str = "queued"
    report: dict | None = None
    error: str | None = None
    output: bytes | None = None

    def public(self):
        return {
            "id": self.id,
            "status": self.status,
            "created_at": self.created_at,
            "report": self.report,
            "error": self.error,
        }


class JobManager:
    """Single-process bounded queue. Originals live only in pending/running work items."""

    def __init__(self, engine: DetectionEngine):
        self.engine = engine
        self.pending = queue.Queue(maxsize=engine.settings.queue_size)
        self.jobs: dict[str, Job] = {}
        self.lock = threading.Lock()
        self.stopping = threading.Event()
        self.thread = threading.Thread(target=self.work, daemon=True, name="document-worker")
        self.thread.start()

    def purge_locked(self):
        now = time.time()
        expired = [
            key
            for key, job in self.jobs.items()
            if job.status in {"succeeded", "failed"}
            and now - job.updated_at > self.engine.settings.job_ttl_seconds
        ]
        for key in expired:
            del self.jobs[key]

    def submit(self, data: bytes, kind: str, options: DocumentOptions):
        self.engine.resolve(options)
        with self.lock:
            self.purge_locked()
            if self.stopping.is_set() or len(self.jobs) >= self.engine.settings.max_jobs:
                raise ServiceError("job_capacity_exceeded", 429)
            job = Job(id=uuid.uuid4().hex)
            self.jobs[job.id] = job
            try:
                self.pending.put_nowait((job.id, data, kind, options))
            except queue.Full as exc:
                del self.jobs[job.id]
                raise ServiceError("document_queue_full", 429) from exc
            return job.public()

    def get(self, job_id):
        with self.lock:
            self.purge_locked()
            if job_id not in self.jobs:
                raise ServiceError("job_not_found_or_expired", 404)
            return self.jobs[job_id]

    def delete(self, job_id):
        with self.lock:
            job = self.jobs.get(job_id)
            if job is None:
                raise ServiceError("job_not_found_or_expired", 404)
            if job.status in {"queued", "running"}:
                raise ServiceError("cannot_delete_active_job", 409)
            del self.jobs[job_id]

    def work(self):
        while not self.stopping.is_set():
            try:
                item = self.pending.get(timeout=1)
            except queue.Empty:
                with self.lock:
                    self.purge_locked()
                continue
            job_id, data, kind, options = item
            job = self.get(job_id)
            try:
                with self.engine.gate:
                    with self.lock:
                        job.status = "running"
                    output, report = process_document(data, kind, options, self.engine)
                with self.lock:
                    job.output, job.report, job.status = output, report, "succeeded"
            except Exception as exc:
                with self.lock:
                    job.error = exc.code if isinstance(exc, ServiceError) else "document_processing_failed"
                    job.status = "failed"
            finally:
                with self.lock:
                    job.updated_at = time.time()
                # Do not keep the last original document in worker locals while idle.
                del item, data, options
                self.pending.task_done()

    def close(self):
        self.stopping.set()
        self.thread.join(timeout=5)
        with self.lock:
            self.jobs.clear()
        while True:
            try:
                self.pending.get_nowait()
                self.pending.task_done()
            except queue.Empty:
                break
