from __future__ import annotations

from collections import defaultdict

from app.config import Settings
from app.privacy_filter_engine import PrivacyFilterEngine
from app.regex_rules import detect_regex_entities
from app.schemas import Entity, InternalEntity, MaskResponse, MaskStats


class TextMasker:
    def __init__(self, settings: Settings, privacy_filter: PrivacyFilterEngine) -> None:
        self.settings = settings
        self.privacy_filter = privacy_filter

    def mask(
        self,
        text: str,
        *,
        return_entities: bool,
        preserve_placeholders: bool,
        return_raw_entities: bool,
    ) -> MaskResponse:
        regex_entities = detect_regex_entities(text)
        model_entities = self.privacy_filter.detect(text)
        merged = merge_spans([*regex_entities, *model_entities])
        placeholders = build_placeholders(merged)

        masked_text = text
        for entity in sorted(merged, key=lambda item: item.start, reverse=True):
            placeholder = placeholders[id(entity)] if preserve_placeholders else ""
            masked_text = masked_text[: entity.start] + placeholder + masked_text[entity.end :]

        response_entities: list[Entity] = []
        if return_entities:
            include_raw = return_raw_entities and self.settings.return_raw_entities_allowed
            for entity in merged:
                response_entities.append(
                    Entity(
                        type=entity.type,
                        placeholder=placeholders[id(entity)] if preserve_placeholders else "",
                        start=entity.start,
                        end=entity.end,
                        source=entity.source,
                        value=text[entity.start : entity.end] if include_raw else None,
                    )
                )

        return MaskResponse(
            masked_text=masked_text,
            entities=response_entities,
            stats=MaskStats(
                entities_count=len(merged),
                model_used=bool(model_entities),
                regex_used=bool(regex_entities),
            ),
        )


def build_placeholders(entities: list[InternalEntity]) -> dict[int, str]:
    counters: dict[str, int] = defaultdict(int)
    placeholders: dict[int, str] = {}
    for entity in entities:
        counters[entity.type.value] += 1
        placeholders[id(entity)] = f"[{entity.type.value}_{counters[entity.type.value]}]"
    return placeholders


def merge_spans(entities: list[InternalEntity]) -> list[InternalEntity]:
    ordered = sorted(entities, key=lambda item: (item.start, -item.length, item.source != "regex"))
    selected: list[InternalEntity] = []
    for candidate in ordered:
        if candidate.start < 0 or candidate.end <= candidate.start:
            continue
        replacement_index: int | None = None
        should_keep = True
        for index, existing in enumerate(selected):
            if not spans_overlap(candidate, existing):
                continue
            winner = choose_span(existing, candidate)
            if winner is existing:
                should_keep = False
                break
            replacement_index = index
        if replacement_index is not None:
            selected[replacement_index] = candidate
        elif should_keep:
            selected.append(candidate)
    return sorted(selected, key=lambda item: item.start)


def spans_overlap(left: InternalEntity, right: InternalEntity) -> bool:
    return left.start < right.end and right.start < left.end


def choose_span(left: InternalEntity, right: InternalEntity) -> InternalEntity:
    if left.length != right.length:
        return left if left.length > right.length else right
    if left.source != right.source:
        return left if left.source == "regex" else right
    return left if left.start <= right.start else right
