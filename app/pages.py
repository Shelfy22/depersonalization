# ruff: noqa: E501

DOCUMENTS_HTML = """
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>PII Filter Service - Documents</title>
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
      max-width: 1280px;
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
    .header-actions {
      display: grid;
      gap: 10px;
      justify-items: end;
    }
    .status {
      min-width: 180px;
      padding: 10px 12px;
      border: 1px solid #d0d5dd;
      border-radius: 8px;
      background: #fff;
      font-size: 14px;
    }
    .nav-button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 180px;
      border-radius: 8px;
      padding: 11px 14px;
      background: #2563eb;
      color: #fff;
      font-weight: 700;
      text-decoration: none;
    }
    .stats {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
      margin-bottom: 16px;
    }
    .stat {
      border: 1px solid #d0d5dd;
      border-radius: 8px;
      background: #fff;
      padding: 12px;
    }
    .stat strong {
      display: block;
      font-size: 24px;
      line-height: 1;
      margin-bottom: 4px;
    }
    .stat span {
      color: #667085;
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
    }
    .layout {
      display: grid;
      grid-template-columns: 320px minmax(0, 1fr);
      gap: 16px;
      align-items: start;
    }
    .side {
      display: grid;
      gap: 16px;
    }
    section {
      background: #fff;
      border: 1px solid #d0d5dd;
      border-radius: 8px;
      padding: 16px;
    }
    .section-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 12px;
    }
    h2 { margin: 0; font-size: 16px; }
    label {
      display: block;
      margin-bottom: 8px;
      font-weight: 600;
    }
    .dropzone {
      min-height: 132px;
      border: 1px dashed #98a2b3;
      border-radius: 8px;
      display: grid;
      place-items: center;
      text-align: center;
      padding: 18px;
      background: #f8fafc;
      cursor: pointer;
    }
    .dropzone input { display: none; }
    .dropzone strong {
      display: block;
      margin-bottom: 8px;
      font-size: 16px;
      color: #111827;
    }
    .dropzone span {
      color: #667085;
      font-size: 13px;
      font-weight: 600;
    }
    input[type="password"] {
      width: 100%;
      border: 1px solid #cbd5e1;
      border-radius: 8px;
      padding: 11px 12px;
      font: inherit;
      color: #111827;
      background: #fff;
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
    button.secondary {
      background: #fff;
      color: #344054;
      border: 1px solid #d0d5dd;
    }
    button:disabled {
      cursor: wait;
      opacity: .65;
    }
    .full { width: 100%; margin-top: 12px; }
    .file-name {
      margin: 10px 0 12px;
      min-height: 18px;
      color: #667085;
      font-size: 13px;
      overflow-wrap: anywhere;
    }
    .doc-list {
      display: grid;
      gap: 8px;
      min-height: 44px;
    }
    .doc-item {
      border: 1px solid #e5e7eb;
      border-radius: 8px;
      padding: 10px;
      background: #f8fafc;
      cursor: pointer;
    }
    .doc-item.active {
      border-color: #2563eb;
      background: #eff6ff;
    }
    .doc-name {
      font-weight: 700;
      overflow-wrap: anywhere;
    }
    .doc-meta {
      margin-top: 5px;
      color: #667085;
      font-size: 12px;
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }
    .review {
      min-height: 560px;
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
    }
    .actions {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: center;
      margin-bottom: 12px;
    }
    .empty {
      min-height: 420px;
      display: grid;
      place-items: center;
      text-align: center;
      color: #667085;
      font-weight: 600;
      border-radius: 8px;
      background: #f8fafc;
      border: 1px solid #e2e8f0;
    }
    .review-grid {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 12px;
      min-height: 0;
    }
    .text-box {
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
      min-height: 0;
    }
    .text-box h3 {
      margin: 0 0 8px;
      font-size: 13px;
      color: #475467;
    }
    pre {
      margin: 0;
      min-height: 360px;
      max-height: 560px;
      overflow: auto;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      border-radius: 8px;
      border: 1px solid #e2e8f0;
      background: #f8fafc;
      padding: 12px;
      color: #111827;
      font: 13px/1.5 Consolas, ui-monospace, monospace;
    }
    .entity-row {
      margin-top: 10px;
      display: flex;
      gap: 7px;
      flex-wrap: wrap;
    }
    .entity-pill {
      border-radius: 999px;
      padding: 5px 8px;
      background: #eef2ff;
      color: #3730a3;
      font-size: 12px;
      font-weight: 700;
    }
    .error {
      margin-top: 12px;
      color: #b42318;
      font-weight: 600;
      white-space: pre-wrap;
    }
    @media (max-width: 980px) {
      header, .layout { grid-template-columns: 1fr; display: grid; }
      .header-actions { justify-items: stretch; }
      .status, .nav-button { width: 100%; }
    }
    @media (max-width: 760px) {
      main { padding: 20px 12px 34px; }
      .stats, .review-grid { grid-template-columns: 1fr; }
      .actions { align-items: stretch; flex-direction: column; }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>PII Filter Service</h1>
        <p>Загрузите текстовый документ, сервис локально прочитает файл в браузере и вернёт обезличенный результат.</p>
      </div>
      <div class="header-actions">
        <a class="nav-button" href="/">Вставить текст</a>
        <div id="opfBadge" class="status">Проверка статуса...</div>
      </div>
    </header>

    <div class="stats">
      <div class="stat"><strong id="documentsCount">0</strong><span>Documents</span></div>
      <div class="stat"><strong id="needsReviewCount">0</strong><span>Needs review</span></div>
      <div class="stat"><strong id="reviewedCount">0</strong><span>Reviewed</span></div>
    </div>

    <div class="layout">
      <div class="side">
        <section>
          <div class="section-head">
            <h2>Добавить документ</h2>
          </div>
          <label class="dropzone" for="fileInput">
            <input id="fileInput" type="file" accept=".txt,.md,.csv,.json,.log,.rtf,text/*,application/json" />
            <span>
              <strong>Выбрать файл</strong>
              <span>TXT, MD, CSV, JSON, LOG, RTF</span>
            </span>
          </label>
          <p class="file-name" id="fileName">Файл не выбран</p>
          <label for="apiKey">X-API-Key</label>
          <input id="apiKey" type="password" value="__API_KEY__" autocomplete="off" />
          <button class="full" id="redactButton" type="button">Обезличить документ</button>
          <div class="error" id="errorBox" hidden></div>
        </section>

        <section>
          <div class="section-head">
            <h2>Документы</h2>
            <button class="secondary" id="clearButton" type="button">Очистить</button>
          </div>
          <div class="doc-list" id="documentList">
            <div class="doc-item"><div class="doc-name">Нет активных документов</div></div>
          </div>
        </section>
      </div>

      <section class="review">
        <div class="actions">
          <h2 id="reviewTitle">Документ не выбран</h2>
          <button class="secondary" id="downloadButton" type="button" disabled>Скачать результат</button>
        </div>
        <div id="reviewEmpty" class="empty">Загрузите файл, чтобы начать проверку.</div>
        <div id="reviewContent" hidden>
          <div class="review-grid">
            <div class="text-box">
              <h3>Исходный текст</h3>
              <pre id="originalText"></pre>
            </div>
            <div class="text-box">
              <h3>Обезличенный текст</h3>
              <pre id="redactedText"></pre>
            </div>
          </div>
          <div class="entity-row" id="entitySummary"></div>
        </div>
      </section>
    </div>
  </main>

  <script>
    const fileInput = document.getElementById("fileInput");
    const fileName = document.getElementById("fileName");
    const apiKey = document.getElementById("apiKey");
    const redactButton = document.getElementById("redactButton");
    const clearButton = document.getElementById("clearButton");
    const downloadButton = document.getElementById("downloadButton");
    const errorBox = document.getElementById("errorBox");
    const documentList = document.getElementById("documentList");
    const documentsCount = document.getElementById("documentsCount");
    const needsReviewCount = document.getElementById("needsReviewCount");
    const reviewedCount = document.getElementById("reviewedCount");
    const reviewTitle = document.getElementById("reviewTitle");
    const reviewEmpty = document.getElementById("reviewEmpty");
    const reviewContent = document.getElementById("reviewContent");
    const originalText = document.getElementById("originalText");
    const redactedText = document.getElementById("redactedText");
    const entitySummary = document.getElementById("entitySummary");
    const opfBadge = document.getElementById("opfBadge");

    const documents = [];
    let selectedId = null;

    fileInput.addEventListener("change", () => {
      fileName.textContent = fileInput.files[0]?.name || "Файл не выбран";
    });

    async function refreshHealth() {
      try {
        const response = await fetch("/health");
        const data = await response.json();
        opfBadge.textContent = `status=${data.status}, model_loaded=${data.model_loaded}, device=${data.device}`;
      } catch {
        opfBadge.textContent = "Статус недоступен";
      }
    }

    function formatBytes(bytes) {
      if (bytes < 1024) return `${bytes} B`;
      if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
      return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
    }

    function readFileAsText(file) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result || ""));
        reader.onerror = () => reject(new Error("Не удалось прочитать файл"));
        reader.readAsText(file, "utf-8");
      });
    }

    async function redactDocument() {
      const file = fileInput.files[0];
      if (!file) {
        showError("Сначала выберите текстовый файл.");
        return;
      }
      errorBox.hidden = true;
      redactButton.disabled = true;
      redactButton.textContent = "Обезличивание...";
      try {
        const text = await readFileAsText(file);
        const response = await fetch("/mask", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-API-Key": apiKey.value,
          },
          body: JSON.stringify({
            text,
            return_entities: true,
            preserve_placeholders: true,
          }),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(JSON.stringify(payload, null, 2));
        }
        const doc = {
          id: crypto.randomUUID ? crypto.randomUUID() : String(Date.now()),
          name: file.name,
          size: file.size,
          original: text,
          redacted: payload.masked_text,
          entities: payload.entities || [],
          stats: payload.stats,
          reviewed: false,
        };
        documents.unshift(doc);
        selectedId = doc.id;
        fileInput.value = "";
        fileName.textContent = "Файл не выбран";
        render();
      } catch (error) {
        showError(error.message);
      } finally {
        redactButton.disabled = false;
        redactButton.textContent = "Обезличить документ";
      }
    }

    function showError(message) {
      errorBox.hidden = false;
      errorBox.textContent = message;
    }

    function render() {
      documentsCount.textContent = documents.length;
      needsReviewCount.textContent = documents.filter((doc) => !doc.reviewed).length;
      reviewedCount.textContent = documents.filter((doc) => doc.reviewed).length;

      if (!documents.length) {
        documentList.innerHTML = '<div class="doc-item"><div class="doc-name">Нет активных документов</div></div>';
      } else {
        documentList.innerHTML = documents.map((doc) => `
          <div class="doc-item ${doc.id === selectedId ? "active" : ""}" data-id="${doc.id}">
            <div class="doc-name">${escapeHtml(doc.name)}</div>
            <div class="doc-meta">
              <span>${formatBytes(doc.size)}</span>
              <span>${doc.stats.entities_count} entities</span>
            </div>
          </div>
        `).join("");
        documentList.querySelectorAll(".doc-item[data-id]").forEach((item) => {
          item.addEventListener("click", () => {
            selectedId = item.dataset.id;
            render();
          });
        });
      }

      const selected = documents.find((doc) => doc.id === selectedId);
      if (!selected) {
        reviewTitle.textContent = "Документ не выбран";
        reviewEmpty.hidden = false;
        reviewContent.hidden = true;
        downloadButton.disabled = true;
        return;
      }
      reviewTitle.textContent = selected.name;
      reviewEmpty.hidden = true;
      reviewContent.hidden = false;
      downloadButton.disabled = false;
      originalText.textContent = selected.original;
      redactedText.textContent = selected.redacted;
      entitySummary.innerHTML = selected.entities.length
        ? selected.entities.map((entity) => `<span class="entity-pill">${entity.type}: ${entity.placeholder}</span>`).join("")
        : '<span class="entity-pill">Сущности не найдены</span>';
    }

    function escapeHtml(value) {
      return value.replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;",
      }[char]));
    }

    function downloadSelected() {
      const selected = documents.find((doc) => doc.id === selectedId);
      if (!selected) return;
      const blob = new Blob([selected.redacted], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = selected.name.replace(/(\\.[^.]+)?$/, ".redacted.txt");
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      selected.reviewed = true;
      render();
    }

    redactButton.addEventListener("click", redactDocument);
    clearButton.addEventListener("click", () => {
      documents.splice(0, documents.length);
      selectedId = null;
      render();
    });
    downloadButton.addEventListener("click", downloadSelected);
    refreshHealth();
    render();
  </script>
</body>
</html>
"""
