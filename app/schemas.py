from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EntityType(StrEnum):
    PERSON = "PERSON"
    ADDRESS = "ADDRESS"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    INN = "INN"
    IIN = "IIN"
    SNILS = "SNILS"
    OGRN = "OGRN"
    OGRNIP = "OGRNIP"
    PASSPORT = "PASSPORT"
    BANK_ACCOUNT = "BANK_ACCOUNT"
    BANK_CARD = "BANK_CARD"
    IP_ADDRESS = "IP_ADDRESS"
    URL = "URL"
    OMS = "OMS"
    DRIVER_LICENSE = "DRIVER_LICENSE"
    MILITARY_ID = "MILITARY_ID"
    BIRTH_CERTIFICATE = "BIRTH_CERTIFICATE"
    ORGANIZATION = "ORGANIZATION"
    CONTRACT_NUMBER = "CONTRACT_NUMBER"
    EMPLOYEE_ID = "EMPLOYEE_ID"
    BIOMETRIC_ID = "BIOMETRIC_ID"
    DATE_OF_BIRTH = "DATE_OF_BIRTH"
    BIRTH_PLACE = "BIRTH_PLACE"
    PASSPORT_ISSUE_DATE = "PASSPORT_ISSUE_DATE"
    JOB_TITLE = "JOB_TITLE"
    WORKPLACE = "WORKPLACE"
    FINANCIAL_AMOUNT = "FINANCIAL_AMOUNT"
    MEDICAL_INFO = "MEDICAL_INFO"
    GEOLOCATION = "GEOLOCATION"
    BIOMETRIC_DATA = "BIOMETRIC_DATA"
    CUSTOM = "CUSTOM"


Profile = Literal["rules", "rubert", "gliner", "hybrid"]
# Organization and contract categories require opt-in; they are not always personal data.
DEFAULT_ENTITIES = [
    e
    for e in EntityType
    if e
    not in {
        EntityType.ORGANIZATION,
        EntityType.CONTRACT_NUMBER,
        EntityType.BIOMETRIC_DATA,
        EntityType.CUSTOM,
    }
]


class Options(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile: Profile | None = None
    entities: list[EntityType] = Field(default_factory=lambda: list(DEFAULT_ENTITIES), min_length=1)
    custom_labels: list[str] = Field(default_factory=list, max_length=12)
    # Exact literal dictionary, never arbitrary client-supplied regex.
    dictionary: list[str] = Field(default_factory=list, max_length=200)
    # Names of persistent server-side dictionaries to apply to this request.
    dictionaries: list[str] = Field(default_factory=list, max_length=20)
    mode: Literal["replace", "redact"] = "replace"

    @model_validator(mode="after")
    def validate_custom(self):
        if any(not label.strip() or len(label) > 80 for label in self.custom_labels):
            raise ValueError("Custom labels must contain 1..80 characters")
        if any(not value.strip() or len(value) > 200 for value in self.dictionary):
            raise ValueError("Dictionary entries must contain 1..200 characters")
        if any(not _valid_dictionary_name(value) for value in self.dictionaries):
            raise ValueError("Dictionary names must use lowercase letters, digits, _ or - (1..64 characters)")
        if self.custom_labels and self.profile in {"rules", "rubert"}:
            raise ValueError("Custom labels require the gliner or hybrid profile")
        return self


class TextRequest(Options):
    text: str = Field(min_length=1, max_length=100_000)


class DocumentOptions(Options):
    output: Literal["text", "document"] = "text"


class Finding(BaseModel):
    start: int
    end: int
    entity_type: str
    score: float
    sources: list[str]


class TextResponse(BaseModel):
    text: str
    findings: list[Finding]
    counts: dict[str, int]
    profile: str
    warnings: list[str]


def _valid_dictionary_name(value: str) -> bool:
    import re

    return bool(re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", value))


class DictionaryUpsert(BaseModel):
    """A complete dictionary replacement. Values are intentionally never returned by read APIs."""

    model_config = ConfigDict(extra="forbid")
    label: str = Field(min_length=2, max_length=40)
    terms: list[str] = Field(min_length=1, max_length=2_000)

    @model_validator(mode="after")
    def validate_terms(self):
        if not _valid_entity_label(self.label):
            raise ValueError("Dictionary label must use uppercase letters, digits or _ (2..40 characters)")
        if any(not term.strip() or len(term) > 200 or "\n" in term or "\r" in term for term in self.terms):
            raise ValueError("Dictionary terms must contain 1..200 characters and no line breaks")
        return self


class DictionaryEntries(BaseModel):
    model_config = ConfigDict(extra="forbid")
    terms: list[str] = Field(min_length=1, max_length=2_000)

    @model_validator(mode="after")
    def validate_terms(self):
        if any(not term.strip() or len(term) > 200 or "\n" in term or "\r" in term for term in self.terms):
            raise ValueError("Dictionary terms must contain 1..200 characters and no line breaks")
        return self


def _valid_entity_label(value: str) -> bool:
    import re

    return bool(re.fullmatch(r"[A-Z][A-Z0-9_]{1,39}", value))
