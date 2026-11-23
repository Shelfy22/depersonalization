"""Persistent literal dictionaries for organisation-specific confidential terms.

The on-disk JSON contains confidential values.  API read operations deliberately
return metadata only; do not expose this directory through a web server or commit it.
"""

import json
import os
import threading
from pathlib import Path

from app.errors import ServiceError
from app.schemas import DictionaryEntries, DictionaryUpsert, _valid_dictionary_name


class DictionaryStore:
    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.RLock()

    def list_metadata(self) -> list[dict[str, object]]:
        with self.lock:
            return [
                {"name": name, "label": item["label"], "entries": len(item["terms"])}
                for name, item in sorted(self._load().items())
            ]

    def replace(self, name: str, payload: DictionaryUpsert) -> dict[str, object]:
        self._require_name(name)
        with self.lock:
            data = self._load()
            data[name] = {"label": payload.label, "terms": self._unique_terms(payload.terms)}
            self._save(data)
            return {"name": name, "label": payload.label, "entries": len(data[name]["terms"])}

    def append(self, name: str, payload: DictionaryEntries) -> dict[str, object]:
        self._require_name(name)
        with self.lock:
            data = self._load()
            if name not in data:
                raise ServiceError("dictionary_not_found", 404)
            data[name]["terms"] = self._unique_terms([*data[name]["terms"], *payload.terms])
            self._save(data)
            return {"name": name, "label": data[name]["label"], "entries": len(data[name]["terms"])}

    def selected_terms(self, names: list[str]) -> list[tuple[str, str]]:
        if not names:
            return []
        with self.lock:
            data = self._load()
            missing = sorted(set(names) - data.keys())
            if missing:
                raise ServiceError("dictionary_not_found", 422)
            # A term may occur in several dictionaries. Preserve the first requested
            # label, rather than returning a potentially revealing combined label.
            selected: dict[str, str] = {}
            for name in names:
                item = data[name]
                for term in item["terms"]:
                    selected.setdefault(term.casefold(), item["label"])
            return [(term, label) for term, label in selected.items()]

    def _load(self) -> dict[str, dict[str, object]]:
        if not self.path.exists():
            return {}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ServiceError("dictionary_store_unavailable", 503) from exc
        if not isinstance(raw, dict):
            raise ServiceError("dictionary_store_unavailable", 503)
        validated: dict[str, dict[str, object]] = {}
        try:
            for name, value in raw.items():
                if not _valid_dictionary_name(name) or not isinstance(value, dict):
                    raise ValueError
                parsed = DictionaryUpsert.model_validate(value)
                validated[name] = {"label": parsed.label, "terms": self._unique_terms(parsed.terms)}
        except (TypeError, ValueError) as exc:
            raise ServiceError("dictionary_store_unavailable", 503) from exc
        return validated

    def _save(self, data: dict[str, dict[str, object]]) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(self.path.suffix + ".tmp")
            temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            os.replace(temporary, self.path)
        except OSError as exc:
            raise ServiceError("dictionary_store_unavailable", 503) from exc

    @staticmethod
    def _unique_terms(terms: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for term in terms:
            cleaned = term.strip()
            key = cleaned.casefold()
            if key not in seen:
                seen.add(key)
                result.append(cleaned)
        return result

    @staticmethod
    def _require_name(name: str) -> None:
        if not _valid_dictionary_name(name):
            raise ServiceError("invalid_dictionary_name", 422)
