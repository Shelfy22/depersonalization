from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from app.schemas import EntityType, InternalEntity


@dataclass(frozen=True)
class RegexRule:
    entity_type: EntityType
    pattern: re.Pattern[str]
    group: int = 0


FLAGS = re.IGNORECASE | re.UNICODE


RULES: tuple[RegexRule, ...] = (
    RegexRule(EntityType.PRIVATE_EMAIL, re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", FLAGS)),
    RegexRule(
        EntityType.PRIVATE_PHONE,
        re.compile(r"(?<!\d)(?:\+7|8)[\s(-]*\d{3}[\s)-]*\d{3}[\s-]*\d{2}[\s-]*\d{2}(?!\d)", FLAGS),
    ),
    RegexRule(EntityType.SNILS, re.compile(r"(?<!\d)\d{3}[-\s]?\d{3}[-\s]?\d{3}[-\s]?\d{2}(?!\d)", FLAGS)),
    RegexRule(EntityType.OGRN, re.compile(r"(?<!\d)(?:\d{13}|\d{15})(?!\d)", FLAGS)),
    RegexRule(EntityType.INN, re.compile(r"(?<!\d)\d{12}(?!\d)", FLAGS)),
    RegexRule(EntityType.INN, re.compile(r"(?<!\d)\d{10}(?!\d)", FLAGS)),
    RegexRule(EntityType.KPP, re.compile(r"(?<!\d)\d{4}[A-ZА-Я0-9]{2}\d{3}(?!\d)", FLAGS)),
    RegexRule(
        EntityType.CONTRACT_ID,
        re.compile(r"\b(?:ETM-\d{3,}|ДГ-\d+(?:/\d{4})?)\b", FLAGS),
    ),
    RegexRule(
        EntityType.CONTRACT_ID,
        re.compile(r"\bдоговор(?:\s+№|\s+N|\s+No|\s+номер)?\s*([A-ZА-Я0-9/_-]{2,})\b", FLAGS),
        group=1,
    ),
    RegexRule(
        EntityType.INTERNAL_URL,
        re.compile(r"\b(?:https?://)?[A-Z0-9.-]+\.etm\.corp(?:/[^\s]*)?\b", FLAGS),
    ),
    RegexRule(
        EntityType.INTERNAL_URL,
        re.compile(r"\b(?:10|192\.168|172\.(?:1[6-9]|2\d|3[01]))(?:\.\d{1,3}){2}\b", FLAGS),
    ),
    RegexRule(
        EntityType.PRIVATE_URL,
        re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b", FLAGS),
    ),
    RegexRule(EntityType.BANK_ACCOUNT, re.compile(r"(?<!\d)\d{20}(?!\d)", FLAGS)),
    RegexRule(EntityType.BIK, re.compile(r"(?<!\d)\d{9}(?!\d)", FLAGS)),
    RegexRule(
        EntityType.PASSPORT,
        re.compile(r"\b(?:паспорт(?:\s+РФ)?\s*)?(?:\d{2}\s?\d{2}\s?\d{6})\b", FLAGS),
    ),
    RegexRule(
        EntityType.EMPLOYEE_ID,
        re.compile(r"\b(?:таб\.?\s*№?|табельный\s+номер|employee\s+id)\s*[:№#-]?\s*([A-ZА-Я0-9_-]{2,})\b", FLAGS),
        group=1,
    ),
)


def detect_regex_entities(text: str, rules: Iterable[RegexRule] = RULES) -> list[InternalEntity]:
    entities: list[InternalEntity] = []
    for rule in rules:
        for match in rule.pattern.finditer(text):
            start = match.start(rule.group)
            end = match.end(rule.group)
            entities.append(
                InternalEntity(
                    type=rule.entity_type,
                    start=start,
                    end=end,
                    source="regex",
                )
            )
    return sorted(entities, key=lambda item: (item.start, -item.length, item.type.value))
