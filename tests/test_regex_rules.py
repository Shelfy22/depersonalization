from __future__ import annotations

from app.masker import merge_spans
from app.regex_rules import detect_regex_entities
from app.schemas import EntityType, InternalEntity


def test_regex_masks_email_phone_inn_and_contract() -> None:
    text = "Позвони +7 999 123-45-67, email ivan.petrov@etm.ru, ИНН 123456789012, договор ETM-4421"

    entities = detect_regex_entities(text)
    types = {entity.type for entity in entities}

    assert EntityType.PRIVATE_EMAIL in types
    assert EntityType.PRIVATE_PHONE in types
    assert EntityType.INN in types
    assert EntityType.CONTRACT_ID in types
    contract = next(entity for entity in entities if entity.type == EntityType.CONTRACT_ID)
    assert text[contract.start : contract.end] == "ETM-4421"


def test_overlapping_spans_keep_longer_and_regex_priority() -> None:
    entities = [
        InternalEntity(type=EntityType.PRIVATE_EMAIL, start=5, end=15, source="privacy_filter"),
        InternalEntity(type=EntityType.PRIVATE_EMAIL, start=5, end=20, source="regex"),
        InternalEntity(type=EntityType.SECRET, start=5, end=20, source="privacy_filter"),
    ]

    merged = merge_spans(entities)

    assert len(merged) == 1
    assert merged[0].start == 5
    assert merged[0].end == 20
    assert merged[0].source == "regex"
