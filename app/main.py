from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.config import Settings, get_settings
from app.logging_config import configure_logging
from app.masker import TextMasker
from app.pages import DOCUMENTS_HTML
from app.privacy_filter_engine import PrivacyFilterEngine
from app.schemas import (
    BatchMaskItemResponse,
    BatchMaskRequest,
    BatchMaskResponse,
    HealthResponse,
    MaskRequest,
    MaskResponse,
)
from app.security import require_api_key

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)
privacy_filter = PrivacyFilterEngine(settings)
masker = TextMasker(settings, privacy_filter)


@asynccontextmanager
async def lifespan(_: FastAPI):
    privacy_filter.load()
    yield


app = FastAPI(title="PII Filter Service", version="0.1.0", lifespan=lifespan)

INDEX_HTML = """
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>PII Filter Service</title>
  <style>
    :root {
      color-scheme: light;
      font-family: Inter, Segoe UI, Arial, sans-serif;
      background: #f5f7fb;
      color: #1f2937;
    }
    * { box-sizing: border-box; }
    body { margin: 0; }
    main {
      max-width: 1120px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }
    header {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-start;
      margin-bottom: 24px;
    }
    h1 { margin: 0 0 8px; font-size: 28px; }
    p { margin: 0; color: #667085; line-height: 1.5; }
    .status {
      min-width: 180px;
      padding: 10px 12px;
      border: 1px solid #d0d5dd;
      border-radius: 8px;
      background: #fff;
      font-size: 14px;
    }
    .grid {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 16px;
    }
    section {
      background: #fff;
      border: 1px solid #d0d5dd;
      border-radius: 8px;
      padding: 16px;
    }
    label {
      display: block;
      margin-bottom: 8px;
      font-weight: 600;
    }
    textarea, input {
      width: 100%;
      border: 1px solid #cbd5e1;
      border-radius: 8px;
      padding: 11px 12px;
      font: inherit;
      color: #111827;
      background: #fff;
    }
    textarea {
      min-height: 320px;
      resize: vertical;
      line-height: 1.45;
    }
    .controls {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 12px;
      align-items: end;
      margin-top: 12px;
    }
    button {
      border: 0;
      border-radius: 8px;
      padding: 12px 18px;
      font-weight: 700;
      cursor: pointer;
      background: #2563eb;
      color: #fff;
    }
    button:disabled {
      cursor: wait;
      opacity: .65;
    }
    .output {
      min-height: 116px;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      padding: 12px;
      border-radius: 8px;
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      line-height: 1.5;
    }
    .meta {
      margin-top: 12px;
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
    }
    .pill {
      border-radius: 8px;
      background: #eef2ff;
      padding: 10px;
      font-size: 13px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 12px;
      font-size: 13px;
    }
    th, td {
      padding: 8px;
      text-align: left;
      border-bottom: 1px solid #e5e7eb;
      vertical-align: top;
    }
    th { color: #475467; }
    .error {
      margin-top: 12px;
      color: #b42318;
      font-weight: 600;
      white-space: pre-wrap;
    }
    @media (max-width: 820px) {
      header, .grid, .controls, .meta { grid-template-columns: 1fr; display: grid; }
      .status { width: 100%; }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>PII Filter Service</h1>
        <p>Вставьте текст, сервис локально замаскирует персональные данные и вернёт обезличенный результат.</p>
      </div>
      <div id="health" class="status">Проверка статуса...</div>
    </header>

    <div class="grid">
      <section>
        <label for="sourceText">Исходный текст</label>
        <textarea id="sourceText">Позвони Ивану Петрову +7 999 123-45-67,
email ivan.petrov@etm.ru, договор ETM-4421</textarea>
        <div class="controls">
          <div>
            <label for="apiKey">X-API-Key</label>
            <input id="apiKey" type="password" value="change-me" autocomplete="off" />
          </div>
          <button id="maskButton" type="button">Маскировать</button>
        </div>
        <div id="error" class="error" hidden></div>
      </section>

      <section>
        <label>Обезличенный текст</label>
        <div id="maskedText" class="output">Результат появится здесь.</div>
        <div class="meta">
          <div class="pill">Сущностей: <strong id="entitiesCount">0</strong></div>
          <div class="pill">Модель: <strong id="modelUsed">-</strong></div>
          <div class="pill">Regex: <strong id="regexUsed">-</strong></div>
        </div>
        <table>
          <thead>
            <tr>
              <th>Тип</th>
              <th>Placeholder</th>
              <th>Источник</th>
              <th>Span</th>
            </tr>
          </thead>
          <tbody id="entitiesTable">
            <tr><td colspan="4">Пока нет данных.</td></tr>
          </tbody>
        </table>
      </section>
    </div>
  </main>

  <script>
    const healthEl = document.getElementById("health");
    const button = document.getElementById("maskButton");
    const sourceText = document.getElementById("sourceText");
    const apiKey = document.getElementById("apiKey");
    const errorEl = document.getElementById("error");
    const maskedText = document.getElementById("maskedText");
    const entitiesCount = document.getElementById("entitiesCount");
    const modelUsed = document.getElementById("modelUsed");
    const regexUsed = document.getElementById("regexUsed");
    const entitiesTable = document.getElementById("entitiesTable");

    async function loadHealth() {
      try {
        const response = await fetch("/health");
        const data = await response.json();
        healthEl.textContent = `status=${data.status}, model_loaded=${data.model_loaded}, device=${data.device}`;
      } catch {
        healthEl.textContent = "Статус недоступен";
      }
    }

    function renderEntities(entities) {
      if (!entities.length) {
        entitiesTable.innerHTML = '<tr><td colspan="4">Сущности не найдены.</td></tr>';
        return;
      }
      entitiesTable.innerHTML = entities.map((entity) => `
        <tr>
          <td>${entity.type}</td>
          <td>${entity.placeholder}</td>
          <td>${entity.source}</td>
          <td>${entity.start}-${entity.end}</td>
        </tr>
      `).join("");
    }

    async function maskText() {
      button.disabled = true;
      errorEl.hidden = true;
      errorEl.textContent = "";
      try {
        const response = await fetch("/mask", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-API-Key": apiKey.value,
          },
          body: JSON.stringify({
            text: sourceText.value,
            return_entities: true,
            preserve_placeholders: true,
          }),
        });
        const data = await response.json();
        if (!response.ok) {
          throw new Error(JSON.stringify(data, null, 2));
        }
        maskedText.textContent = data.masked_text;
        entitiesCount.textContent = data.stats.entities_count;
        modelUsed.textContent = data.stats.model_used ? "да" : "нет";
        regexUsed.textContent = data.stats.regex_used ? "да" : "нет";
        renderEntities(data.entities || []);
      } catch (error) {
        errorEl.hidden = false;
        errorEl.textContent = error.message;
      } finally {
        button.disabled = false;
      }
    }

    button.addEventListener("click", maskText);
    loadHealth();
  </script>
</body>
</html>
"""

if settings.cors_enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins) or ["http://localhost"],
        allow_credentials=False,
        allow_methods=["POST", "GET"],
        allow_headers=["X-API-Key", "Content-Type"],
    )


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index() -> HTMLResponse:
    return HTMLResponse(INDEX_HTML)


@app.get("/documents", response_class=HTMLResponse, include_in_schema=False)
async def documents() -> HTMLResponse:
    return HTMLResponse(DOCUMENTS_HTML)


def validate_text_size(text: str, current_settings: Settings = settings) -> None:
    if len(text) > current_settings.max_text_length:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Text is too large",
        )


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", model_loaded=privacy_filter.model_loaded, device=settings.device)


@app.post("/mask", response_model=MaskResponse, dependencies=[Depends(require_api_key)])
async def mask(payload: MaskRequest, request: Request) -> MaskResponse:
    validate_text_size(payload.text)
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    started = time.perf_counter()
    response = masker.mask(
        payload.text,
        return_entities=payload.return_entities,
        preserve_placeholders=payload.preserve_placeholders,
        return_raw_entities=payload.return_raw_entities,
    )
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    logger.info(
        "mask_completed",
        extra={
            "request_id": request_id,
            "text_length": len(payload.text),
            "entities_count": response.stats.entities_count,
            "entity_types": sorted({entity.type.value for entity in response.entities}),
            "duration_ms": duration_ms,
        },
    )
    return response


@app.post("/mask/batch", response_model=BatchMaskResponse, dependencies=[Depends(require_api_key)])
async def mask_batch(payload: BatchMaskRequest, request: Request) -> BatchMaskResponse:
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    started = time.perf_counter()
    items: list[BatchMaskItemResponse] = []
    total_entities = 0
    for item in payload.items:
        validate_text_size(item.text)
        result = masker.mask(
            item.text,
            return_entities=payload.return_entities,
            preserve_placeholders=payload.preserve_placeholders,
            return_raw_entities=payload.return_raw_entities,
        )
        total_entities += result.stats.entities_count
        items.append(
            BatchMaskItemResponse(
                id=item.id,
                masked_text=result.masked_text,
                entities=result.entities if payload.return_entities else [],
            )
        )
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    logger.info(
        "mask_batch_completed",
        extra={
            "request_id": request_id,
            "text_length": sum(len(item.text) for item in payload.items),
            "entities_count": total_entities,
            "duration_ms": duration_ms,
        },
    )
    return BatchMaskResponse(items=items)
