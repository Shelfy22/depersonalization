import hmac
from contextlib import asynccontextmanager
from pathlib import PurePath

from fastapi import FastAPI, File, Form, Request, Security, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.security import APIKeyHeader
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from app.config import Settings
from app.engine import DetectionEngine
from app.errors import ServiceError
from app.jobs import JobManager
from app.schemas import (
    DictionaryEntries,
    DictionaryUpsert,
    DocumentOptions,
    EntityType,
    TextRequest,
    TextResponse,
)


class BoundaryMiddleware:
    """Authenticate and bound the actual body before JSON/multipart parsing."""

    def __init__(self, app, settings):
        self.app, self.settings = app, settings

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        protected = scope["path"].startswith("/v1")
        headers = dict(scope["headers"])
        if protected:
            supplied = headers.get(b"x-api-key", b"")
            expected = self.settings.api_key.get_secret_value().encode()
            if not expected or not hmac.compare_digest(supplied, expected):
                return await JSONResponse({"error": "unauthorized"}, 401)(scope, receive, send)
        limit = (
            self.settings.max_upload_mb * 1024**2 + 128 * 1024
            if scope["path"] == "/v1/documents"
            else self.settings.max_text_chars * 8 + 128 * 1024
        )
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > limit:
                return await JSONResponse({"error": "request_body_limit_exceeded"}, 413)(scope, receive, send)
            if not message.get("more_body", False):
                break
        delivered = False

        async def bounded_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        async def private_send(message):
            if message["type"] == "http.response.start":
                message["headers"] = list(message["headers"]) + [
                    (b"cache-control", b"no-store"),
                    (b"x-content-type-options", b"nosniff"),
                ]
            await send(message)

        await self.app(scope, bounded_receive, private_send)


def create_app(settings: Settings | None = None, engine: DetectionEngine | None = None):
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(application):
        if len(settings.api_key.get_secret_value()) < 24:
            raise RuntimeError("Set ANON_API_KEY to a random secret of at least 24 characters")
        # Loading failure stops startup: never silently fall back to regex-only filtering.
        application.state.engine = engine or await run_in_threadpool(DetectionEngine, settings)
        application.state.jobs = JobManager(application.state.engine)
        yield
        application.state.jobs.close()

    application = FastAPI(
        title="Russian PII Filter",
        version="0.1.0",
        lifespan=lifespan,
        dependencies=[Security(APIKeyHeader(name="X-API-Key", auto_error=False))],
    )
    application.add_middleware(BoundaryMiddleware, settings=settings)

    @application.exception_handler(ServiceError)
    async def service_error(request, exc):
        return JSONResponse({"error": exc.code}, status_code=exc.status)

    @application.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # FastAPI's default errors echo rejected input; this API handles confidential input.
        return JSONResponse(
            {"error": "invalid_request", "types": sorted({e["type"] for e in exc.errors()})}, status_code=422
        )

    @application.exception_handler(Exception)
    async def unexpected_error(request, exc):
        return JSONResponse({"error": "processing_failed"}, status_code=500)

    @application.get("/health/live")
    def live():
        return {"status": "ok"}

    @application.get("/health/ready")
    def ready(request: Request):
        return {"status": "ready" if hasattr(request.app.state, "engine") else "starting"}

    @application.get("/v1/capabilities")
    def capabilities(request: Request):
        detector = request.app.state.engine
        profiles = ["rules"]
        if detector.rubert is not None:
            profiles.append("rubert")
        if detector.gliner is not None:
            profiles.append("gliner")
        if detector.rubert is not None and detector.gliner is not None:
            profiles.append("hybrid")
        return {
            "profiles": profiles,
            "default_profile": settings.default_profile,
            "entities": [str(e) for e in EntityType],
            "formats": ["txt", "docx", "xlsx", "pdf (requires pdf extra)"],
            "ocr": False,
            "unsupported_without_media_pipeline": ["BIOMETRIC_DATA"],
            "dictionary_api": "/v1/dictionaries",
            "max_document_chars": settings.max_document_chars,
            "models": {
                "rubert": settings.rubert_model if detector.rubert else None,
                "gliner": settings.gliner_model if detector.gliner else None,
            },
        }

    @application.get("/v1/dictionaries")
    def dictionaries(request: Request):
        """List dictionary metadata. Terms are confidential and are never returned."""
        return {"dictionaries": request.app.state.engine.dictionaries.list_metadata()}

    @application.put("/v1/dictionaries/{name}")
    def replace_dictionary(request: Request, name: str, payload: DictionaryUpsert):
        """Create or completely replace a dictionary. Use the entries endpoint to add terms."""
        return request.app.state.engine.dictionaries.replace(name, payload)

    @application.post("/v1/dictionaries/{name}/entries")
    def append_dictionary_entries(request: Request, name: str, payload: DictionaryEntries):
        return request.app.state.engine.dictionaries.append(name, payload)

    def run_text(request, payload, analyze=False):
        detector = request.app.state.engine
        if len(payload.text) > settings.max_text_chars:
            raise ServiceError("text_limit_exceeded", 413)
        if not detector.gate.acquire(blocking=False):
            raise ServiceError("inference_busy_retry_later", 429)
        try:
            result = detector.anonymize(payload.text, payload)
            if analyze:
                return result.model_dump(exclude={"text"})
            return result
        except ServiceError:
            raise
        except Exception as exc:
            raise ServiceError("inference_failed", 503) from exc
        finally:
            detector.gate.release()

    @application.post("/v1/anonymize", response_model=TextResponse)
    def anonymize(request: Request, payload: TextRequest):
        return run_text(request, payload)

    @application.post("/v1/analyze")
    def analyze(request: Request, payload: TextRequest):
        return run_text(request, payload, analyze=True)

    @application.post("/v1/documents", status_code=202)
    async def documents(request: Request, file: UploadFile = File(...), options: str = Form("{}")):
        try:
            if len(options) > 64_000:
                raise ServiceError("options_limit_exceeded", 413)
            try:
                parsed = DocumentOptions.model_validate_json(options)
            except (ValidationError, ValueError) as exc:
                raise ServiceError("invalid_document_options") from exc
            kind = PurePath(file.filename or "").suffix.lower().lstrip(".")
            if kind not in {"txt", "docx", "xlsx", "pdf"}:
                raise ServiceError("unsupported_file_type", 415)
            data = await file.read(settings.max_upload_mb * 1024**2 + 1)
            if len(data) > settings.max_upload_mb * 1024**2:
                raise ServiceError("upload_limit_exceeded", 413)
            if not data:
                raise ServiceError("empty_file")
            job = request.app.state.jobs.submit(data, kind, parsed)
            return {
                **job,
                "status_url": f"/v1/jobs/{job['id']}",
                "result_url": f"/v1/jobs/{job['id']}/result",
            }
        finally:
            await file.close()

    @application.get("/v1/jobs/{job_id}")
    def job_status(request: Request, job_id: str):
        return request.app.state.jobs.get(job_id).public()

    @application.get("/v1/jobs/{job_id}/result")
    def job_result(request: Request, job_id: str):
        job = request.app.state.jobs.get(job_id)
        if job.status != "succeeded":
            raise ServiceError("job_result_not_available", 409)
        return Response(
            job.output,
            media_type=job.report["output_mime"],
            headers={"Content-Disposition": f'attachment; filename="{job.report["output_name"]}"'},
        )

    @application.delete("/v1/jobs/{job_id}", status_code=204)
    def delete_job(request: Request, job_id: str):
        request.app.state.jobs.delete(job_id)
        return Response(status_code=204)

    return application


app = create_app()
