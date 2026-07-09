from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    PRIVATE_PERSON = "PRIVATE_PERSON"
    PRIVATE_PHONE = "PRIVATE_PHONE"
    PRIVATE_EMAIL = "PRIVATE_EMAIL"
    PRIVATE_ADDRESS = "PRIVATE_ADDRESS"
    PRIVATE_DATE = "PRIVATE_DATE"
    PRIVATE_URL = "PRIVATE_URL"
    ACCOUNT_NUMBER = "ACCOUNT_NUMBER"
    SECRET = "SECRET"
    INN = "INN"
    KPP = "KPP"
    SNILS = "SNILS"
    OGRN = "OGRN"
    CONTRACT_ID = "CONTRACT_ID"
    INTERNAL_URL = "INTERNAL_URL"
    BANK_ACCOUNT = "BANK_ACCOUNT"
    BIK = "BIK"
    PASSPORT = "PASSPORT"
    EMPLOYEE_ID = "EMPLOYEE_ID"


class Entity(BaseModel):
    type: EntityType
    placeholder: str
    start: int
    end: int
    source: Literal["regex", "privacy_filter"]
    value: str | None = None


class InternalEntity(BaseModel):
    type: EntityType
    start: int
    end: int
    source: Literal["regex", "privacy_filter"]

    @property
    def length(self) -> int:
        return self.end - self.start


class MaskRequest(BaseModel):
    text: str = Field(..., min_length=0)
    return_entities: bool = False
    preserve_placeholders: bool = True
    return_raw_entities: bool = False


class MaskStats(BaseModel):
    entities_count: int
    model_used: bool
    regex_used: bool


class MaskResponse(BaseModel):
    masked_text: str
    entities: list[Entity] = Field(default_factory=list)
    stats: MaskStats


class BatchItem(BaseModel):
    id: str
    text: str


class BatchMaskRequest(BaseModel):
    items: list[BatchItem]
    return_entities: bool = False
    preserve_placeholders: bool = True
    return_raw_entities: bool = False


class BatchMaskItemResponse(BaseModel):
    id: str
    masked_text: str
    entities: list[Entity] = Field(default_factory=list)


class BatchMaskResponse(BaseModel):
    items: list[BatchMaskItemResponse]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    model_loaded: bool
    device: str
