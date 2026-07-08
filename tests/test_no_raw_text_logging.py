from __future__ import annotations

import logging

from fastapi.testclient import TestClient

from app.main import app


def test_no_raw_text_in_logs(caplog) -> None:
    raw_text = "Секретная почта ivan.petrov@etm.ru"
    client = TestClient(app)

    with caplog.at_level(logging.INFO):
        response = client.post(
            "/mask",
            headers={"X-API-Key": "change-me", "X-Request-ID": "req-test"},
            json={"text": raw_text, "return_entities": True},
        )

    assert response.status_code == 200
    logs = "\n".join(record.getMessage() for record in caplog.records)
    assert raw_text not in logs
    assert "ivan.petrov@etm.ru" not in logs
