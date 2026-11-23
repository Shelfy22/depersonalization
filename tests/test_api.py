import time


def wait_job(client, job_id):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        job = client.get(f"/v1/jobs/{job_id}").json()
        if job["status"] in {"succeeded", "failed"}:
            return job
        time.sleep(0.02)
    raise AssertionError("Job timed out")


def test_authentication_and_no_input_echo(client):
    assert client.get("/health/live", headers={"X-API-Key": ""}).status_code == 200
    assert client.post("/v1/anonymize", json={"text": "secret"}, headers={"X-API-Key": ""}).status_code == 401
    response = client.post("/v1/anonymize", json={"text": {"secret": "private@corp.ru"}})
    assert response.status_code == 422
    assert "private@corp.ru" not in response.text and "secret" not in response.text
    response = client.post("/v1/anonymize", json={"text": "ok", "private@corp.ru": "unexpected"})
    assert "private@corp.ru" not in response.text


def test_text_api_and_analyze_no_originals(client):
    response = client.post("/v1/anonymize", json={"text": "Пишите: test@example.ru"})
    assert response.status_code == 200
    assert response.json()["text"] == "Пишите: [EMAIL_1]"
    assert response.headers["cache-control"] == "no-store"
    assert "test@example.ru" not in response.text
    assert "text" not in client.post("/v1/analyze", json={"text": "test@example.ru"}).json()


def test_unavailable_profile_is_error(client):
    assert client.post("/v1/anonymize", json={"text": "Иванов", "profile": "hybrid"}).status_code == 503


def test_persistent_dictionary_api_does_not_disclose_terms(client):
    created = client.put(
        "/v1/dictionaries/projects",
        json={"label": "PROJECT", "terms": ["Проект Альфа", "Внутренний код 42"]},
    )
    assert created.status_code == 200
    assert created.json() == {"name": "projects", "label": "PROJECT", "entries": 2}
    updated = client.post("/v1/dictionaries/projects/entries", json={"terms": ["Проект Бета"]})
    assert updated.status_code == 200 and updated.json()["entries"] == 3
    listed = client.get("/v1/dictionaries")
    assert listed.status_code == 200
    assert listed.json()["dictionaries"] == [{"name": "projects", "label": "PROJECT", "entries": 3}]
    assert "Проект Альфа" not in listed.text
    response = client.post(
        "/v1/anonymize",
        json={"text": "Передать Проект Альфа", "dictionaries": ["projects"]},
    )
    assert response.status_code == 200
    assert response.json()["text"] == "Передать [PROJECT_1]"


def test_busy_inference_returns_429(client, engine):
    with engine.gate:
        assert client.post("/v1/anonymize", json={"text": "hello"}).status_code == 429


def test_document_job_roundtrip_and_delete(client):
    response = client.post(
        "/v1/documents", files={"file": ("Иванов.txt", "Почта: hello@example.ru".encode())}
    )
    assert response.status_code == 202
    job_id = response.json()["id"]
    job = wait_job(client, job_id)
    assert job["status"] == "succeeded"
    assert "hello@example.ru" not in str(job) and "Иванов" not in str(job)
    output = client.get(f"/v1/jobs/{job_id}/result")
    assert output.text == "Почта: [EMAIL_1]"
    assert client.delete(f"/v1/jobs/{job_id}").status_code == 204
    assert client.get(f"/v1/jobs/{job_id}").status_code == 404


def test_document_errors_and_actual_body_limit(client):
    assert client.post("/v1/documents", files={"file": ("test.exe", b"not a document")}).status_code == 415
    response = client.post("/v1/documents", files={"file": ("secret.docx", b"private@corp.ru")})
    job = wait_job(client, response.json()["id"])
    assert job["status"] == "failed" and job["error"] == "invalid_or_unsupported_document"
    assert "private@corp.ru" not in str(job)
    assert client.get(f"/v1/jobs/{job['id']}/result").status_code == 409
    response = client.post("/v1/documents", files={"file": ("test.txt", b"a" * (2 * 1024**2))})
    assert response.status_code == 413
