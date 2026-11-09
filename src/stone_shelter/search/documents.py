"""Validated search projections shared by lexical and vector adapters."""

from typing import Final, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from stone_shelter.adoption.enums import AdoptionStatus, CaseEventType
from stone_shelter.catalog.enums import StoneSize, StoneType
from stone_shelter.search.enums import DocumentKind

SEARCH_SCHEMA_VERSION: Final[int] = 1
PROJECTION_VERSION: Final[int] = 1
LANGUAGE_VERSION: Final[str] = "en"

class SearchDocument(BaseModel):
    """Common content, provenance, and revision fields for search evidence."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)
    language: str = Field(min_length=1)
    source_key: str = Field(min_length=1)

    schema_version: int = Field(ge=1)
    projection_version: int = Field(ge=1)
    source_revision: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class OperationalSearchDocument(SearchDocument):
    """Source identities and current-state filters for an individual stone."""

    stone_external_id: UUID
    case_external_id: UUID
    case_number: str = Field(min_length=1)
    stone_type: StoneType
    stone_size: StoneSize
    adoption_status: AdoptionStatus
    current_shelter_id: UUID


class StoneSearchDocument(OperationalSearchDocument):
    """Searchable identity and biography of one stone."""

    document_kind: Literal[DocumentKind.STONE] = DocumentKind.STONE


class ProfileSearchDocument(OperationalSearchDocument):
    """One existing profile rendered as labeled source facts."""

    document_kind: Literal[DocumentKind.PROFILE] = DocumentKind.PROFILE


class CaseEventSearchDocument(OperationalSearchDocument):
    """One historical event with its source identity and occurrence time."""

    document_kind: Literal[DocumentKind.CASE_EVENT] = DocumentKind.CASE_EVENT
    event_external_id: UUID
    event_type: CaseEventType
    occurred_at: AwareDatetime


class EncyclopediaSectionSearchDocument(SearchDocument):
    """One reference section, independent of any individual stone or case."""

    document_kind: Literal[DocumentKind.ENCYCLOPEDIA_SECTION] = DocumentKind.ENCYCLOPEDIA_SECTION
    source_path: str = Field(min_length=1)
    section_path: list[str] = Field(min_length=1)
    stone_type: StoneType | None = None
