import ipaddress
import re
from collections.abc import Callable
from dataclasses import dataclass

from presidio_analyzer import EntityRecognizer, RecognizerResult


def digits(value: str) -> str:
    return re.sub(r"\D", "", value)


def valid_inn(value: str) -> bool:
    n = digits(value)
    if len(set(n)) <= 1:
        return False

    def check(weights, index):
        return sum(int(c) * w for c, w in zip(n, weights, strict=False)) % 11 % 10 == int(n[index])

    if len(n) == 10:
        return check([2, 4, 10, 3, 5, 9, 4, 6, 8], 9)
    return (
        len(n) == 12
        and check([7, 2, 4, 10, 3, 5, 9, 4, 6, 8], 10)
        and check([3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8], 11)
    )


def valid_snils(value: str) -> bool:
    n = digits(value)
    if len(n) != 11 or len(set(n)) <= 1:
        return False
    total = sum(int(c) * w for c, w in zip(n[:9], range(9, 0, -1), strict=True))
    return (total % 101) % 100 == int(n[-2:])


def valid_ogrn(value: str) -> bool:
    n = digits(value)
    return len(set(n)) > 1 and (
        len(n) == 13
        and int(n[:-1]) % 11 % 10 == int(n[-1])
        or len(n) == 15
        and int(n[:-1]) % 13 % 10 == int(n[-1])
    )


def valid_card(value: str) -> bool:
    n = digits(value)
    if not 13 <= len(n) <= 19 or len(set(n)) <= 1:
        return False
    total = 0
    for i, c in enumerate(reversed(n)):
        v = int(c) * (2 if i % 2 else 1)
        total += v - 9 if v > 9 else v
    return total % 10 == 0


def valid_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


@dataclass(frozen=True)
class Rule:
    kind: str
    pattern: str
    score: float = 0.85
    validator: Callable[[str], bool] | None = None
    context: str | None = None
    group: int = 0


RULES = [
    # ruBERT may find a surname but leave initials beside it. This pattern joins
    # with the adjacent PERSON span during result merging.
    Rule("PERSON", r"(?<![А-ЯЁA-Z])[А-ЯЁA-Z]\.[ \t]*[А-ЯЁA-Z]\.(?![А-ЯЁA-Z])", 0.92),
    Rule("EMAIL", r"(?<![\w.+-])[\w.+-]{1,64}@[\w-]{1,63}(?:\.[\w-]{1,63}){1,5}(?![\w-])", 0.99),
    Rule("PHONE", r"(?<!\w)(?:\+7|8)[ \t(.-]*\d{3}[ \t).-]*\d{3}[ \t.-]*\d{2}[ \t.-]*\d{2}(?!\d)", 0.9),
    Rule("PHONE", r"(?:тел(?:ефон)?\.?|моб\.?)\s*[:=]?\s*(\+?\d[\d ()-]{5,23}\d)", group=1),
    Rule("INN", r"(?<!\d)(?:\d{12}|\d{10})(?!\d)", 0.99, valid_inn, r"инн"),
    Rule(
        "SNILS",
        r"(?<!\d)\d{3}[ -]?\d{3}[ -]?\d{3}[ -]?\d{2}(?!\d)",
        0.99,
        valid_snils,
        r"снилс|страхов\w*\s+свидетельств",
    ),
    Rule("OGRN", r"(?<!\d)\d{13}(?!\d)", 0.99, valid_ogrn, r"огрн(?!ип)"),
    Rule("OGRNIP", r"(?<!\d)\d{15}(?!\d)", 0.99, valid_ogrn, r"огрнип"),
    Rule(
        "PASSPORT",
        r"(?:серия\s*)?\d{2}[ -]?\d{2}\s*(?:,|;)?\s*(?:номер|№|N)\s*\d{6}(?!\d)",
        0.96,
    ),
    Rule("PASSPORT", r"(?<!\d)\d{2}[ -]?\d{2}[ \t-]?\d{6}(?!\d)", context=r"паспорт|серия"),
    Rule("BANK_ACCOUNT", r"(?<!\d)\d{20}(?!\d)", context=r"сч[её]т|р/с|к/с|account"),
    Rule("BANK_CARD", r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)", 0.98, valid_card, r"карт[аыуе]|card"),
    Rule("IP_ADDRESS", r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])", 0.95, valid_ip),
    Rule("URL", r"\bhttps?://[^\s<>\"\[\]]{1,1000}", 0.9),
    Rule("CONTRACT_NUMBER", r"(?:договор\w*|контракт\w*)\s*(?:№|номер|N)\s*([\w/-]{1,60})", group=1),
    Rule(
        "DATE_OF_BIRTH",
        r"(?:дата\s+рождения|родивш[а-яё]*|родил[а-яё]*)[^0-9]{0,50}(\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+\d{4}(?:\s+года)?)",
        0.95,
        group=1,
    ),
    Rule(
        "DATE_OF_BIRTH",
        r"(?:дата\s+рождения|родивш[а-яё]*|родил[а-яё]*|д[./]р\.?)\s*[:=]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
        group=1,
    ),
    Rule(
        "DATE_OF_BIRTH",
        r"(?<!\d)(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})(?:\s+года\s+рождения)",
        0.95,
        group=1,
    ),
    Rule(
        "EMPLOYEE_ID",
        r"(?:табельн\w*\s+номер(?:\s+сотрудника)?|employee\s*id)\s*[:—-]?\s*([A-Za-zА-Яа-яЁё]{2,12}[-_/]\d{2,8}(?:[-_/]\d{2,12}){1,4})",
        0.98,
        group=1,
    ),
    # These categories only match an explicit Russian context.  They intentionally
    # do not attempt to hide every date, amount, organisation or place name.
    Rule(
        "PASSPORT_ISSUE_DATE",
        r"(?:дата\s+выдачи|выдан[а-яё]*)[^0-9]{0,30}(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
        0.94,
        group=1,
    ),
    Rule(
        "BIRTH_PLACE",
        r"(?:место\s+рождения)\s*[:—-]?\s*([^.;\n]{2,120})",
        0.93,
        group=1,
    ),
    Rule(
        "JOB_TITLE",
        r"(?:должность|назначен[а-яё]*\s+на\s+должность|работает\s+в\s+должности)\s*[:—-]?\s*([^.;\n]{2,120})",
        0.9,
        group=1,
    ),
    Rule(
        "WORKPLACE",
        r"(?:место\s+работы|работает\s+в|трудится\s+в)\s*[:—-]?\s*([^.;\n]{2,120})",
        0.88,
        group=1,
    ),
    Rule(
        "FINANCIAL_AMOUNT",
        r"(?:оклад|зарплат\w*|доход\w*|задолженн\w*|долг\w*)[^0-9]{0,35}(\d{1,3}(?:[ \u00a0]\d{3})*(?:[,.]\d{2})?\s*(?:₽|руб\.?|RUB)?)",
        0.91,
        group=1,
    ),
    Rule(
        "MEDICAL_INFO",
        r"(?:диагноз|результат(?:ы)?\s+(?:анализ(?:а|ов)|обследования)|медицинск\w*\s+заключени\w*)\s*[:—-]?\s*([^.;\n]{2,300})",
        0.93,
        group=1,
    ),
    Rule(
        "GEOLOCATION",
        r"(?:геолокаци\w*|координат\w*|местоположени\w*)[^0-9-]{0,35}(-?\d{1,2}\.\d{3,8}\s*[,;]\s*-?\d{1,3}\.\d{3,8})",
        0.95,
        group=1,
    ),
]


class RussianRulesRecognizer(EntityRecognizer):
    def __init__(self):
        self.rules = [(r, re.compile(r.pattern, re.IGNORECASE)) for r in RULES]
        super().__init__(supported_entities=sorted({r.kind for r in RULES}), supported_language="ru")

    def load(self):
        pass

    def analyze(self, text, entities, nlp_artifacts=None):
        results = []
        for rule, pattern in self.rules:
            if rule.kind not in entities:
                continue
            for match in pattern.finditer(text):
                value = match.group(rule.group)
                context = text[max(0, match.start() - 45) : match.start()]
                contextual = bool(rule.context and re.search(rule.context, context, re.IGNORECASE))
                valid = rule.validator(value) if rule.validator else not rule.context
                if not valid and not contextual:
                    continue
                score = rule.score if valid else 0.65
                results.append(RecognizerResult(rule.kind, *match.span(rule.group), score))
        return results
