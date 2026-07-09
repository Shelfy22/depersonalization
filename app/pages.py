# ruff: noqa: E501

DOCUMENTS_HTML = """
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Document Redaction Review</title>
  <style>
    :root {
      color-scheme: dark;
      font-family: Inter, Segoe UI, Arial, sans-serif;
      background: #07120b;
      color: #edf7ef;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at 15% 85%, rgba(65, 189, 172, .14), transparent 32%),
        linear-gradient(135deg, #07120b 0%, #0d1911 45%, #08110b 100%);
    }
    main {
      width: min(1440px, 100%);
      margin: 0 auto;
      padding: 28px 26px 38px;
    }
    header {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 22px;
      align-items: end;
      margin-bottom: 18px;
    }
    .hello {
      color: #91a394;
      font-size: 13px;
      font-weight: 700;
      margin-bottom: 3px;
    }
    h1 {
      margin: 0;
      font-size: 32px;
      line-height: 1.05;
      letter-spacing: 0;
    }
    .stats {
      display: grid;
      grid-template-columns: repeat(3, minmax(120px, 1fr));
      gap: 8px;
    }
    .stat {
      border: 1px solid rgba(255, 255, 255, .08);
      border-radius: 8px;
      background: rgba(255, 255, 255, .045);
      padding: 10px 12px;
      box-shadow: inset 0 0 0 1px rgba(255, 255, 255, .02);
    }
    .stat strong {
      display: block;
      font-size: 22px;
      line-height: 1;
      margin-bottom: 4px;
    }
    .stat span {
      color: #8fa194;
      font-size: 11px;
      font-weight: 800;
      text-transform: uppercase;
    }
    .layout {
      display: grid;
      grid-template-columns: 280px 340px minmax(0, 1fr);
      gap: 14px;
      align-items: start;
    }
    .panel {
      border: 1px solid rgba(255, 255, 255, .08);
      border-radius: 8px;
      background: rgba(255, 255, 255, .045);
      box-shadow: 0 20px 55px rgba(0, 0, 0, .28);
      padding: 14px;
    }
    .panel-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 12px;
    }
    h2 {
      margin: 0;
      font-size: 16px;
      line-height: 1.2;
    }
    .badge {
      border-radius: 999px;
      background: rgba(77, 207, 157, .16);
      color: #7ee3b8;
      padding: 5px 10px;
      font-size: 11px;
      font-weight: 800;
    }
    .dropzone {
      min-height: 116px;
      border: 1px dashed rgba(255, 255, 255, .16);
      border-radius: 8px;
      display: grid;
      place-items: center;
      text-align: center;
      padding: 18px;
      background: rgba(255, 255, 255, .035);
      cursor: pointer;
    }
    .dropzone input { display: none; }
    .dropzone strong {
      display: block;
      margin-bottom: 8px;
      font-size: 16px;
    }
    .dropzone span {
      color: #98a79b;
      font-size: 12px;
      font-weight: 700;
    }
    .file-name {
      margin: 10px 0 0;
      min-height: 18px;
      color: #b7c6ba;
      font-size: 12px;
      overflow-wrap: anywhere;
    }
    label {
      display: block;
      margin: 12px 0 7px;
      color: #dce8df;
      font-size: 12px;
      font-weight: 800;
    }
    input[type="password"] {
      width: 100%;
      border: 1px solid rgba(255, 255, 255, .12);
      border-radius: 8px;
      padding: 10px 11px;
      background: rgba(0, 0, 0, .2);
      color: #fff;
      font: inherit;
    }
    button {
      border: 0;
      border-radius: 8px;
      padding: 11px 14px;
      font-weight: 900;
      cursor: pointer;
      background: #45c6b8;
      color: #08211d;
      box-shadow: 0 8px 20px rgba(69, 198, 184, .18);
    }
    button.secondary {
      background: rgba(255, 255, 255, .07);
      color: #e8f2ea;
      box-shadow: none;
      border: 1px solid rgba(255, 255, 255, .08);
    }
    button:disabled {
      opacity: .55;
      cursor: wait;
    }
    .full { width: 100%; margin-top: 10px; }
    .tabs {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 6px;
      padding: 4px;
      border: 1px solid rgba(255, 255, 255, .08);
      border-radius: 8px;
      background: rgba(0, 0, 0, .18);
      margin-bottom: 12px;
    }
    .tab {
      padding: 8px;
      border-radius: 6px;
      text-align: center;
      font-weight: 800;
      color: #98a79b;
    }
    .tab.active {
      background: rgba(255, 255, 255, .08);
      color: #effaf1;
    }
    .doc-list {
      display: grid;
      gap: 8px;
      min-height: 44px;
    }
    .doc-item {
      border: 1px solid rgba(255, 255, 255, .08);
      border-radius: 8px;
      padding: 10px;
      background: rgba(0, 0, 0, .18);
      cursor: pointer;
    }
    .doc-item.active {
      border-color: rgba(69, 198, 184, .8);
      background: rgba(69, 198, 184, .1);
    }
    .doc-name {
      font-weight: 850;
      overflow-wrap: anywhere;
    }
    .doc-meta {
      margin-top: 5px;
      color: #95a69a;
      font-size: 12px;
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }
    .review {
      min-height: 520px;
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
    }
    .empty {
      min-height: 410px;
      display: grid;
      place-items: center;
      text-align: center;
      color: #9baa9e;
      font-weight: 700;
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
      color: #cfe1d3;
    }
    pre {
      margin: 0;
      min-height: 360px;
      max-height: 560px;
      overflow: auto;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      border-radius: 8px;
      border: 1px solid rgba(255, 255, 255, .08);
      background: rgba(0, 0, 0, .24);
      padding: 12px;
      color: #e9f5ed;
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
      background: rgba(255, 255, 255, .08);
      color: #d7e6da;
      font-size: 12px;
      font-weight: 800;
    }
    .actions {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: center;
      margin-bottom: 12px;
    }
    .error {
      margin-top: 10px;
      color: #ffb4a8;
      font-size: 13px;
      white-space: pre-wrap;
    }
    @media (max-width: 1100px) {
      .layout { grid-template-columns: 1fr; }
      header { grid-template-columns: 1fr; }
      .stats { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    }
    @media (max-width: 760px) {
      main { padding: 18px 12px 30px; }
      .stats, .review-grid { grid-template-columns: 1fr; }
      h1 { font-size: 27px; }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <div class="hello">Local PII Filter</div>
        <h1>Redaction Review</h1>
      </div>
      <div class="stats">
        <div class="stat"><strong id="documentsCount">0</strong><span>Documents</span></div>
        <div class="stat"><strong id="needsReviewCount">0</strong><span>Needs review</span></div>
        <div class="stat"><strong id="reviewedCount">0</strong><span>Reviewed</span></div>
      </div>
    </header>

    <div class="layout">
      <section class="panel">
        <div class="panel-head">
          <h2>Add Document</h2>
          <span class="badge" id="opfBadge">OPF checking</span>
        </div>
        <label class="dropzone" for="fileInput">
          <input id="fileInput" type="file" accept=".txt,.md,.csv,.json,.log,.rtf,text/*,application/json" />
          <span>
            <strong>Choose file</strong>
            <span>TXT, MD, CSV, JSON, LOG, RTF</span>
          </span>
        </label>
        <p class="file-name" id="fileName">No file selected</p>
        <label for="apiKey">X-API-Key</label>
        <input id="apiKey" type="password" value="change-me" autocomplete="off" />
        <button class="full" id="redactButton" type="button">Add and Redact</button>
        <div class="error" id="errorBox" hidden></div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <h2>Documents</h2>
          <button class="secondary" id="clearButton" type="button">Clear</button>
        </div>
        <div class="tabs">
          <div class="tab active">Active</div>
          <div class="tab">Archived</div>
        </div>
        <div class="doc-list" id="documentList">
          <div class="doc-item"><div class="doc-name">No active documents</div></div>
        </div>
      </section>

      <section class="panel review">
        <div class="actions">
          <h2 id="reviewTitle">No document selected</h2>
          <button class="secondary" id="downloadButton" type="button" disabled>Download result</button>
        </div>
        <div id="reviewEmpty" class="empty">Import a file to start review.</div>
        <div id="reviewContent" hidden>
          <div class="review-grid">
            <div class="text-box">
              <h3>Original text</h3>
              <pre id="originalText"></pre>
            </div>
            <div class="text-box">
              <h3>Redacted text</h3>
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
      fileName.textContent = fileInput.files[0]?.name || "No file selected";
    });

    async function refreshHealth() {
      try {
        const response = await fetch("/health");
        const data = await response.json();
        opfBadge.textContent = data.model_loaded ? "OPF active" : "OPF inactive";
      } catch {
        opfBadge.textContent = "OPF unknown";
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
        reader.onerror = () => reject(new Error("Could not read file"));
        reader.readAsText(file, "utf-8");
      });
    }

    async function redactDocument() {
      const file = fileInput.files[0];
      if (!file) {
        showError("Choose a text file first.");
        return;
      }
      errorBox.hidden = true;
      redactButton.disabled = true;
      redactButton.textContent = "Redacting...";
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
        fileName.textContent = "No file selected";
        render();
      } catch (error) {
        showError(error.message);
      } finally {
        redactButton.disabled = false;
        redactButton.textContent = "Add and Redact";
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
        documentList.innerHTML = '<div class="doc-item"><div class="doc-name">No active documents</div></div>';
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
        reviewTitle.textContent = "No document selected";
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
        : '<span class="entity-pill">No entities found</span>';
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
