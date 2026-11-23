"""Smoke check an already running local service using the key from .env. Synthetic data only."""

import argparse
import json
import time

import httpx

from app.config import Settings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    settings = Settings()
    with httpx.Client(
        base_url=args.url, headers={"X-API-Key": settings.api_key.get_secret_value()}, timeout=120
    ) as client:
        client.get("/health/ready").raise_for_status()
        response = client.post(
            "/v1/anonymize", json={"text": "Документы Иванова Ивана Ивановича. Почта test@example.ru"}
        )
        response.raise_for_status()
        payload = response.json()
        assert "test@example.ru" not in payload["text"]
        assert payload["counts"].get("PERSON", 0) > 0
        response = client.post(
            "/v1/documents",
            files={
                "file": ("synthetic.txt", "Документы Иванова Ивана Ивановича. Почта test@example.ru".encode())
            },
        )
        response.raise_for_status()
        job_id = response.json()["id"]
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            response = client.get(f"/v1/jobs/{job_id}")
            response.raise_for_status()
            job = response.json()
            if job["status"] == "failed":
                raise RuntimeError(job["error"])
            if job["status"] == "succeeded":
                break
            time.sleep(0.1)
        else:
            raise TimeoutError("Document job timed out")
        output = client.get(f"/v1/jobs/{job_id}/result")
        output.raise_for_status()
        assert "test@example.ru" not in output.text and "[PERSON_" in output.text
        client.delete(f"/v1/jobs/{job_id}").raise_for_status()
        print(
            json.dumps(
                {"http_smoke": "passed", "message": payload["text"], "document": output.text},
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
