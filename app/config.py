from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv(override=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ANON_", env_file=".env", extra="ignore")

    api_key: SecretStr = SecretStr("")
    default_profile: Literal["rules", "rubert", "gliner", "hybrid"] = "rubert"
    enable_rubert: bool = True
    enable_gliner: bool = False
    rubert_model: str = "redmadrobot-rnd/rubert-base-pii-ner"
    rubert_revision: str = "main"
    gliner_model: str = "urchade/gliner_multi_pii-v1"
    gliner_revision: str = "main"
    local_files_only: bool = True
    device: str = "cpu"
    torch_threads: int = Field(default=4, ge=1, le=64)
    rubert_threshold: float = Field(default=0.45, ge=0, le=1)
    gliner_threshold: float = Field(default=0.5, ge=0, le=1)
    max_text_chars: int = Field(default=100_000, ge=1)
    max_document_chars: int = Field(default=2_000_000, ge=1)
    max_upload_mb: int = Field(default=25, ge=1, le=200)
    max_unpacked_mb: int = Field(default=150, ge=1, le=500)
    max_pages: int = Field(default=500, ge=1)
    max_cells: int = Field(default=200_000, ge=1)
    queue_size: int = Field(default=4, ge=1, le=32)
    max_jobs: int = Field(default=32, ge=1, le=1000)
    job_ttl_seconds: int = Field(default=1800, ge=10)
    dictionary_path: Path = Path("data/dictionaries.json")
