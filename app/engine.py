import re
import threading
from collections import Counter

from app.config import Settings
from app.detectors import GlinerRecognizer, RubertRecognizer
from app.dictionaries import DictionaryStore
from app.errors import ServiceError
from app.rules import RussianRulesRecognizer
from app.schemas import Finding, Options, TextResponse


def merge_findings(text: str, findings: list[Finding]) -> list[Finding]:
    """Union intersecting intervals: a lower score must not leave a detected suffix exposed."""
    merged: list[Finding] = []
    normalized = [_extend_person_case_ending(text, item) for item in findings]
    for item in sorted(normalized, key=lambda f: (f.start, f.end, f.entity_type)):
        if not 0 <= item.start < item.end <= len(text):
            raise ServiceError("detector_returned_invalid_offsets", 503)
        previous = merged[-1] if merged else None
        gap = text[previous.end : item.start] if previous else ""
        adjacent = (
            previous
            and item.entity_type == previous.entity_type
            and (
                not gap
                or (
                    item.start - previous.end <= 3
                    and gap.isspace()
                    and item.entity_type in {"PERSON", "ADDRESS"}
                )
                or (
                    item.entity_type == "PERSON" and bool(re.fullmatch(r"\s+(?:[А-ЯЁA-Z]\.[ \t]*){1,3}", gap))
                )
            )
        )
        if previous and (item.start < previous.end or adjacent):
            kinds = {previous.entity_type, item.entity_type}
            previous.end = max(previous.end, item.end)
            previous.score = max(previous.score, item.score)
            previous.sources = sorted(set(previous.sources + item.sources))
            if len(kinds) > 1:
                previous.entity_type = "SENSITIVE"
        else:
            merged.append(item.model_copy(deep=True))
    return merged


def _extend_person_case_ending(text: str, finding: Finding) -> Finding:
    """Include attached Russian declension endings left outside a model span."""
    if finding.entity_type != "PERSON":
        return finding
    end = finding.end
    while end < len(text) and text[end].isalpha() and text[end].islower():
        end += 1
    return finding.model_copy(update={"end": end})


class Masker:
    """Request-local consistent placeholders; original values never leave this object."""

    def __init__(self, mode="replace"):
        self.mode = mode
        self.values: dict[tuple[str, str], str] = {}
        self.counts: Counter = Counter()

    def apply(self, text, findings):
        pieces = []
        cursor = 0
        for f in findings:
            pieces.append(text[cursor : f.start])
            pieces.append(self.replacement(text, f))
            cursor = f.end
        pieces.append(text[cursor:])
        return "".join(pieces)

    def replacement(self, text, finding):
        if self.mode == "redact":
            return "[REDACTED]"
        key = (finding.entity_type, text[finding.start : finding.end].casefold())
        if key not in self.values:
            self.counts[finding.entity_type] += 1
            self.values[key] = f"[{finding.entity_type}_{self.counts[finding.entity_type]}]"
        return self.values[key]


class DetectionEngine:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.gate = threading.Lock()
        self.rules = RussianRulesRecognizer()
        self.dictionaries = DictionaryStore(settings.dictionary_path)
        self.rubert = RubertRecognizer(settings) if settings.enable_rubert else None
        self.gliner = GlinerRecognizer(settings) if settings.enable_gliner else None
        self.resolve(Options())

    def resolve(self, options: Options):
        profile = options.profile or self.settings.default_profile
        if profile in {"rubert", "hybrid"} and self.rubert is None:
            raise ServiceError("rubert_not_enabled", 503)
        if profile in {"gliner", "hybrid"} and self.gliner is None:
            raise ServiceError("gliner_not_enabled", 503)
        if options.custom_labels and profile not in {"gliner", "hybrid"}:
            raise ServiceError("custom_labels_require_gliner")
        return profile

    def detect(self, text: str, options: Options):
        profile = self.resolve(options)
        entities = [str(e) for e in options.entities]
        findings = []
        recognizers = [self.rules]
        if profile in {"rubert", "hybrid"}:
            recognizers.append(self.rubert)
        if profile in {"gliner", "hybrid"}:
            recognizers.append(self.gliner)
        for recognizer in recognizers:
            if recognizer is self.gliner:
                results = recognizer.analyze_custom(text, entities, options.custom_labels)
            else:
                results = recognizer.analyze(text, entities, None)
            findings.extend(
                Finding(
                    start=r.start,
                    end=r.end,
                    entity_type=r.entity_type,
                    score=round(r.score, 4),
                    sources=[recognizer.name],
                )
                for r in results
            )
        # Dictionaries are literal terms only, never caller-provided regular expressions.
        dictionary_terms: list[tuple[str, str]] = [(value, "CUSTOM") for value in options.dictionary]
        dictionary_terms.extend(self.dictionaries.selected_terms(options.dictionaries))
        for value, entity_type in dictionary_terms:
            pattern = re.compile(re.escape(value), re.IGNORECASE)
            findings.extend(
                Finding(start=m.start(), end=m.end(), entity_type=entity_type, score=1, sources=["dictionary"])
                for m in pattern.finditer(text)
            )
        return merge_findings(text, findings)

    def anonymize(self, text: str, options: Options, masker: Masker | None = None):
        findings = self.detect(text, options)
        warnings = []
        if self.resolve(options) == "rules":
            warnings.append("rules_only_does_not_detect_names_or_addresses")
        if any(f.entity_type == "SENSITIVE" for f in findings):
            warnings.append("overlapping_entity_types_masked_as_union")
        anonymized_text = (masker or Masker(options.mode)).apply(text, findings)
        self.assert_no_residual_structured_identifiers(anonymized_text, options)
        return TextResponse(
            text=anonymized_text,
            findings=findings,
            counts=dict(Counter(f.entity_type for f in findings)),
            profile=self.resolve(options),
            warnings=warnings,
        )

    def assert_no_residual_structured_identifiers(self, text: str, options: Options) -> None:
        """Fail closed if a selected high-confidence identifier remains after masking."""
        audited = {"IIN", "SNILS", "BIOMETRIC_ID", "EMPLOYEE_ID"} & {str(item) for item in options.entities}
        if self.rules.analyze(text, list(audited), None):
            raise ServiceError("residual_structured_identifier_detected", 422)
