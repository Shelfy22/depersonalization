from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from typing import Any

from app.config import Settings
from app.schemas import EntityType, InternalEntity

logger = logging.getLogger(__name__)


LABEL_MAP: dict[str, EntityType] = {
    "private_person": EntityType.PRIVATE_PERSON,
    "private_phone": EntityType.PRIVATE_PHONE,
    "private_email": EntityType.PRIVATE_EMAIL,
    "private_address": EntityType.PRIVATE_ADDRESS,
    "private_date": EntityType.PRIVATE_DATE,
    "private_url": EntityType.PRIVATE_URL,
    "account_number": EntityType.ACCOUNT_NUMBER,
    "secret": EntityType.SECRET,
}


class PrivacyFilterEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._redactor: Any | None = None
        self._loaded = False
        self._load_error: str | None = None

    @property
    def model_loaded(self) -> bool:
        return self._loaded

    def load(self) -> None:
        if not self.settings.model_enabled:
            logger.warning("privacy_filter_disabled")
            return
        try:
            from opf._api import OPF

            self._redactor = OPF(
                model=self.settings.checkpoint,
                device=self.settings.device,  # type: ignore[arg-type]
                output_mode="typed",
                output_text_only=False,
            )
            self._redactor.get_runtime()
            self._loaded = True
            logger.info("privacy_filter_loaded", extra={"device": self.settings.device})
        except Exception as exc:
            self._load_error = exc.__class__.__name__
            logger.warning("privacy_filter_python_api_unavailable", extra={"error_type": self._load_error})

    def detect(self, text: str) -> list[InternalEntity]:
        if not self.settings.model_enabled:
            return []
        if self._redactor is not None:
            return self._detect_with_python_api(text)
        return self._detect_with_subprocess(text)

    def _detect_with_python_api(self, text: str) -> list[InternalEntity]:
        result = self._redactor.redact(text)
        spans = getattr(result, "detected_spans", ())
        return self._normalize_spans(spans)

    def _detect_with_subprocess(self, text: str) -> list[InternalEntity]:
        command = [
            sys.executable,
            "-m",
            "opf",
            "--format",
            "json",
            "--device",
            self.settings.device,
        ]
        if self.settings.checkpoint:
            command.extend(["--checkpoint", self.settings.checkpoint])
        command.append(text)

        env = os.environ.copy()
        if self.settings.checkpoint:
            env["OPF_CHECKPOINT"] = self.settings.checkpoint

        completed = subprocess.run(
            command,
            env=env,
            capture_output=True,
            text=True,
            timeout=self.settings.opf_subprocess_timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            logger.error("privacy_filter_subprocess_failed", extra={"returncode": completed.returncode})
            return []
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError:
            logger.error("privacy_filter_subprocess_invalid_json")
            return []
        return self._normalize_spans(payload.get("detected_spans", []))

    @staticmethod
    def _normalize_spans(spans: Any) -> list[InternalEntity]:
        entities: list[InternalEntity] = []
        for span in spans:
            label = getattr(span, "label", None) if not isinstance(span, dict) else span.get("label")
            start = getattr(span, "start", None) if not isinstance(span, dict) else span.get("start")
            end = getattr(span, "end", None) if not isinstance(span, dict) else span.get("end")
            entity_type = LABEL_MAP.get(str(label))
            if entity_type is None or not isinstance(start, int) or not isinstance(end, int) or end <= start:
                continue
            entities.append(InternalEntity(type=entity_type, start=start, end=end, source="privacy_filter"))
        return entities
