from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_mask_requires_api_key() -> None:
    response = client.post("/mask", json={"text": "ivan.petrov@etm.ru"})

    assert response.status_code == 401


def test_mask_endpoint_masks_entities() -> None:
    response = client.post(
        "/mask",
        headers={"X-API-Key": "change-me"},
        json={
            "text": "Телефон +7 999 123-45-67, email ivan.petrov@etm.ru, договор ETM-4421",
            "return_entities": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "ivan.petrov@etm.ru" not in payload["masked_text"]
    assert "+7 999 123-45-67" not in payload["masked_text"]
    assert "ETM-4421" not in payload["masked_text"]
    assert payload["stats"]["entities_count"] >= 3
    assert all("value" not in entity or entity["value"] is None for entity in payload["entities"])


def test_too_long_text_returns_413() -> None:
    response = client.post(
        "/mask",
        headers={"X-API-Key": "change-me"},
        json={"text": "x" * 101},
    )

    assert response.status_code == 413


def test_batch_masks_items() -> None:
    response = client.post(
        "/mask/batch",
        headers={"X-API-Key": "change-me"},
        json={"items": [{"id": "msg_1", "text": "email ivan.petrov@etm.ru"}], "return_entities": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["id"] == "msg_1"
    assert "ivan.petrov@etm.ru" not in payload["items"][0]["masked_text"]
