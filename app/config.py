from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


@dataclass(frozen=True)
class Settings:
    api_key: str | None = os.getenv("PII_FILTER_API_KEY")
    allow_no_auth: bool = _get_bool("ALLOW_NO_AUTH", False)
    model_path: str | None = os.getenv("MODEL_PATH")
    opf_checkpoint: str | None = os.getenv("OPF_CHECKPOINT")
    device: str = os.getenv("DEVICE", "cpu")
    max_text_length: int = _get_int("MAX_TEXT_LENGTH", 50_000)
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    return_raw_entities_allowed: bool = _get_bool("RETURN_RAW_ENTITIES_ALLOWED", False)
    cors_enabled: bool = _get_bool("CORS_ENABLED", False)
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "").split(",")
        if origin.strip()
    )
    model_enabled: bool = _get_bool("MODEL_ENABLED", True)
    opf_subprocess_timeout_seconds: int = _get_int("OPF_SUBPROCESS_TIMEOUT_SECONDS", 120)

    @property
    def checkpoint(self) -> str | None:
        return self.opf_checkpoint or self.model_path


def get_settings() -> Settings:
    return Settings()
