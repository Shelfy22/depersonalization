"""Presidio-compatible local model adapters. No inference API calls."""

import re

from presidio_analyzer import EntityRecognizer, RecognizerResult

from app.config import Settings
from app.errors import ServiceError

RUBERT_LABELS = {
    **dict.fromkeys(["FIRST_NAME", "LAST_NAME", "MIDDLE_NAME", "PER", "PERSON"], "PERSON"),
    **dict.fromkeys(
        ["COUNTRY", "REGION", "DISTRICT", "CITY", "STREET", "HOUSE", "LOCATION", "LOC"], "ADDRESS"
    ),
    "EMAIL": "EMAIL",
    "PHONE": "PHONE",
    "URL": "URL",
    "IP_ADDRESS": "IP_ADDRESS",
    "PASSPORT": "PASSPORT",
    "INN": "INN",
    "SNILS": "SNILS",
    "OMS": "OMS",
    "CREDIT_CARD": "BANK_CARD",
    "DRIVER_LICENSE": "DRIVER_LICENSE",
    "MILITARY_ID": "MILITARY_ID",
    "BIRTH_CERTIFICATE": "BIRTH_CERTIFICATE",
}
GLINER_LABELS = {
    "person": "PERSON",
    "address": "ADDRESS",
    "email": "EMAIL",
    "phone number": "PHONE",
    "tax identification number": "INN",
    "social security number": "SNILS",
    "passport number": "PASSPORT",
    "bank account number": "BANK_ACCOUNT",
    "credit card number": "BANK_CARD",
    "ip address": "IP_ADDRESS",
    "url": "URL",
    "health insurance number": "OMS",
    "driver's license number": "DRIVER_LICENSE",
    "military id": "MILITARY_ID",
    "birth certificate number": "BIRTH_CERTIFICATE",
    "organization": "ORGANIZATION",
    "contract number": "CONTRACT_NUMBER",
    "employee id": "EMPLOYEE_ID",
    "date of birth": "DATE_OF_BIRTH",
    "birth place": "BIRTH_PLACE",
    "passport issue date": "PASSPORT_ISSUE_DATE",
    "job title": "JOB_TITLE",
    "workplace": "WORKPLACE",
    "salary": "FINANCIAL_AMOUNT",
    "income": "FINANCIAL_AMOUNT",
    "debt": "FINANCIAL_AMOUNT",
    "medical information": "MEDICAL_INFO",
    "geolocation": "GEOLOCATION",
    "biometric data": "BIOMETRIC_DATA",
    "company registration number": "OGRN",
    "individual entrepreneur registration number": "OGRNIP",
}


def character_windows(text, size=12_000, overlap=600):
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        yield start, text[start:end]
        if end == len(text):
            break
        start = end - overlap


class RubertRecognizer(EntityRecognizer):
    def __init__(self, settings: Settings):
        self.settings = settings
        super().__init__(supported_entities=sorted(set(RUBERT_LABELS.values())), supported_language="ru")

    def load(self):
        import torch
        from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline

        s = self.settings
        torch.set_num_threads(s.torch_threads)
        kw = dict(revision=s.rubert_revision, local_files_only=s.local_files_only, trust_remote_code=False)
        tokenizer = AutoTokenizer.from_pretrained(s.rubert_model, use_fast=True, **kw)
        if not tokenizer.is_fast:
            raise ServiceError("rubert_requires_fast_tokenizer", 503)
        model = AutoModelForTokenClassification.from_pretrained(s.rubert_model, use_safetensors=True, **kw)
        labels = {label.removeprefix("B-").removeprefix("I-") for label in model.config.id2label.values()}
        if labels - {"O"} - RUBERT_LABELS.keys():
            raise ServiceError("unsupported_rubert_label_schema", 503)
        tokenizer.model_max_length = min(512, model.config.max_position_embeddings)
        self.pipe = pipeline(
            "token-classification",
            model=model,
            tokenizer=tokenizer,
            aggregation_strategy="simple",
            device=s.device,
        )

    def analyze(self, text, entities, nlp_artifacts=None):
        results = []
        for offset, chunk in character_windows(text):
            # Token-aware overlapping windows inside every bounded character block.
            for item in self.pipe(chunk, stride=128, batch_size=1):
                kind = RUBERT_LABELS.get(item["entity_group"])
                value = item["word"]
                if (
                    kind in entities
                    and float(item["score"]) >= self.settings.rubert_threshold
                    and usable_model_span(kind, value)
                ):
                    results.append(
                        RecognizerResult(
                            kind, offset + item["start"], offset + item["end"], float(item["score"])
                        )
                    )
        return results


def usable_model_span(kind: str | None, value: str) -> bool:
    """Reject fragments that cannot safely be redacted as standalone entities.

    Token classifiers may label an isolated abbreviation such as ``г`` as a city
    or a single digit as a house number. Those fragments are not useful PII by
    themselves and would be disastrous in layout-preserving PDF redaction.
    """
    compact = re.sub(r"[^\w]", "", value, flags=re.UNICODE)
    if kind == "PERSON":
        return sum(char.isalpha() for char in compact) >= 2
    if kind == "ADDRESS":
        return len(compact) >= 3
    return bool(compact)


class GlinerRecognizer(EntityRecognizer):
    def __init__(self, settings: Settings):
        self.settings = settings
        super().__init__(
            supported_entities=sorted(set(GLINER_LABELS.values()) | {"CUSTOM"}), supported_language="ru"
        )

    def load(self):
        import torch
        from gliner import GLiNER

        s = self.settings
        torch.set_num_threads(s.torch_threads)
        self.model = GLiNER.from_pretrained(
            s.gliner_model,
            revision=s.gliner_revision,
            local_files_only=s.local_files_only,
            load_tokenizer=True,
        )
        self.model.to(s.device)
        self.model.eval()
        self.tokenizer = self.model.data_processor.transformer_tokenizer
        self.tokenizer.model_max_length = 512

    def windows(self, text, labels):
        # Bound BOTH word count and subwords, accounting for label prompts.
        prompt_size = len(self.tokenizer.encode(" ".join(labels), add_special_tokens=False)) + 4 * len(labels)
        budget = min(256, int(getattr(self.model.config, "max_len", 384)) - prompt_size - 32)
        if budget < 64:
            raise ServiceError("gliner_labels_exceed_context_budget")
        for offset, chunk in character_windows(text, 4000, 400):
            words = list(re.finditer(r"\S+", chunk))
            start = 0
            while start < len(words):
                end = min(start + budget // 2, len(words))
                while end > start:
                    piece = chunk[words[start].start() : words[end - 1].end()]
                    if len(self.tokenizer.encode(piece, add_special_tokens=False)) <= budget:
                        break
                    end -= 1
                if end == start:
                    # Never silently truncate an unbroken token/identifier.
                    raise ServiceError("gliner_token_exceeds_context_budget")
                yield offset + words[start].start(), piece
                if end == len(words):
                    break
                start = max(start + 1, end - min(16, (end - start) // 3))

    def analyze_custom(self, text, entities, custom_labels):
        label_map = {label: kind for label, kind in GLINER_LABELS.items() if kind in entities}
        label_map.update({label: "CUSTOM" for label in custom_labels})
        if not label_map:
            return []
        results = []
        # Small label groups preserve context space and avoid excessively long prompts.
        labels = list(label_map)
        for i in range(0, len(labels), 6):
            group = labels[i : i + 6]
            for offset, chunk in self.windows(text, group):
                for item in self.model.predict_entities(
                    chunk, group, threshold=self.settings.gliner_threshold
                ):
                    kind = label_map[item["label"]]
                    results.append(
                        RecognizerResult(
                            kind, offset + item["start"], offset + item["end"], float(item["score"])
                        )
                    )
        return results

    def analyze(self, text, entities, nlp_artifacts=None):
        return self.analyze_custom(text, entities, [])
