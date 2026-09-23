from datetime import datetime
from typing import Annotated

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator

CompanyName = Annotated[str, Field(min_length=1, max_length=120)]
Website = Annotated[AnyHttpUrl, Field(max_length=2048)]
Industry = Annotated[str, Field(min_length=1, max_length=100)]
Location = Annotated[str, Field(min_length=1, max_length=255)]
Notes = Annotated[str, Field(max_length=5000)]


def _strip_required(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("Value cannot be blank")
    return normalized


def _strip_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


class CompanyCreate(BaseModel):
    name: CompanyName
    website: Website | None = None
    industry: Industry | None = None
    location: Location | None = None
    notes: Notes | None = None

    model_config = ConfigDict(extra="forbid")

    _normalize_name = field_validator("name")(_strip_required)
    _normalize_optional_text = field_validator(
        "industry",
        "location",
        "notes",
    )(_strip_optional)


class CompanyUpdate(BaseModel):
    name: CompanyName | None = None
    website: Website | None = None
    industry: Industry | None = None
    location: Location | None = None
    notes: Notes | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("Company name cannot be null")
        return _strip_required(value)

    _normalize_optional_text = field_validator(
        "industry",
        "location",
        "notes",
    )(_strip_optional)


class CompanyResponse(BaseModel):
    id: int
    name: str
    website: AnyHttpUrl | None = None
    industry: str | None = None
    location: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompanyListResponse(BaseModel):
    items: list[CompanyResponse]
    total: int
    page: int
    page_size: int
