from __future__ import annotations

import logging
import sys


class SafeExtraFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        allowed = {
            "request_id",
            "text_length",
            "entities_count",
            "entity_types",
            "duration_ms",
            "device",
            "returncode",
            "error_type",
        }
        extras = {key: value for key, value in record.__dict__.items() if key in allowed}
        if extras:
            return f"{base} {extras}"
        return base


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(SafeExtraFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
