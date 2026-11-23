import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.engine import DetectionEngine
from app.main import create_app

KEY = "test-secret-key-at-least-24-characters"


@pytest.fixture
def settings(tmp_path):
    return Settings(
        _env_file=None,
        api_key=KEY,
        default_profile="rules",
        enable_rubert=False,
        enable_gliner=False,
        max_upload_mb=1,
        job_ttl_seconds=10,
        dictionary_path=tmp_path / "dictionaries.json",
    )


@pytest.fixture
def engine(settings):
    return DetectionEngine(settings)


@pytest.fixture
def client(settings, engine):
    with TestClient(create_app(settings, engine)) as test_client:
        test_client.headers["X-API-Key"] = KEY
        yield test_client
