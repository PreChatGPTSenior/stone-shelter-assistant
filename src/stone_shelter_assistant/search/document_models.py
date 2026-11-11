"""Validated search projections shared by lexical and vector adapters."""

from typing import Annotated, Final, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictBool, TypeAdapter

from stone_shelter_assistant.search.enums import (
    AccommodationFactType,
    CompatibilityVerdict,
    DocumentKind,
)
from stone_shelter_assistant.stones.enums import (
    AdoptionStatus,
    CareLevel,
    CaseEventType,
    SocializationTrait,
    StoneSize,
    StoneType,
)

SEARCH_SCHEMA_VERSION: Final[int] = 1
PROJECTION_VERSION: Final[int] = 1
DEFAULT_LANGUAGE: Final[str] = "en"


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
    """Identities shared by a stone card and its historical events."""

    stone_external_id: UUID
    case_external_id: UUID
    case_number: str = Field(min_length=1)
    stone_type: StoneType


class StoneSearchDocument(OperationalSearchDocument):
    """One stone's biography, profile, and current case filters."""

    document_kind: Literal[DocumentKind.STONE] = DocumentKind.STONE
    stone_size: StoneSize
    adoption_status: AdoptionStatus
    current_shelter_id: UUID
    socialization_traits: list[SocializationTrait] = Field(default_factory=list)
    care_level: CareLevel | None = None


class CaseEventSearchDocument(OperationalSearchDocument):
    """One historical event with its source identity and occurrence time."""

    document_kind: Literal[DocumentKind.CASE_EVENT] = DocumentKind.CASE_EVENT
    event_external_id: UUID
    event_type: CaseEventType
    occurred_at: int = Field(description="Microseconds since the Unix epoch (UTC)")


class KnowledgeSearchDocument(SearchDocument):
    """Shared source and type filters for the reference collection."""

    source_path: str = Field(min_length=1)
    stone_types: list[StoneType] = Field(default_factory=list, max_length=2)


class EncyclopediaSectionSearchDocument(KnowledgeSearchDocument):
    """One reference section, independent of any individual stone or case."""

    document_kind: Literal[DocumentKind.ENCYCLOPEDIA_SECTION] = DocumentKind.ENCYCLOPEDIA_SECTION
    section_path: list[str] = Field(min_length=1)
    stone_types: list[StoneType] = Field(default_factory=list, max_length=1)


## compatibility


class CompatibilitySearchDocument(KnowledgeSearchDocument):
    """Searchable evidence from the stone type compatibility guide."""


class CompatibilityReadingRulesSearchDocument(CompatibilitySearchDocument):
    document_kind: Literal[DocumentKind.COMPATIBILITY_READING_RULES] = (
        DocumentKind.COMPATIBILITY_READING_RULES
    )


class CompatibilityCondition(BaseModel):
    """One author-defined mandatory condition, grounded in the pair rule's text."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    fact_type: AccommodationFactType
    expected_value: StrictBool
    source_quote: str = Field(min_length=1)


class CompatibilityPairSearchDocument(CompatibilitySearchDocument):
    """Searchable advice for a pair of stone types."""

    document_kind: Literal[DocumentKind.COMPATIBILITY_PAIR] = DocumentKind.COMPATIBILITY_PAIR
    stone_types: list[StoneType] = Field(min_length=2, max_length=2)
    pair_key: str = Field(min_length=1)
    verdict: CompatibilityVerdict
    conditions: list[CompatibilityCondition] = Field(default_factory=list)


class CompatibilityTypePortraitSearchDocument(CompatibilitySearchDocument):
    """Searchable portrait of one stone type."""

    document_kind: Literal[DocumentKind.COMPATIBILITY_TYPE_PORTRAIT] = (
        DocumentKind.COMPATIBILITY_TYPE_PORTRAIT
    )
    stone_types: list[StoneType] = Field(min_length=1, max_length=1)


type KnowledgeDocument = Annotated[
    EncyclopediaSectionSearchDocument
    | CompatibilityPairSearchDocument
    | CompatibilityTypePortraitSearchDocument
    | CompatibilityReadingRulesSearchDocument,
    Field(discriminator="document_kind"),
]
KNOWLEDGE_DOCUMENT_ADAPTER: TypeAdapter[KnowledgeDocument] = TypeAdapter(KnowledgeDocument)


type KnowledgeLanguage = Annotated[str, Field(pattern=r"^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$")]
type KnowledgeDocumentKind = Literal[
    DocumentKind.ENCYCLOPEDIA_SECTION,
    DocumentKind.COMPATIBILITY_PAIR,
    DocumentKind.COMPATIBILITY_TYPE_PORTRAIT,
    DocumentKind.COMPATIBILITY_READING_RULES,
]


class KnowledgeSearchFilters(BaseModel):
    """Exact filters shared by the two knowledge searches."""

    model_config = ConfigDict(extra="forbid")

    document_kind: KnowledgeDocumentKind | None = None
    stone_type: StoneType | None = None
    language: KnowledgeLanguage | None = None
