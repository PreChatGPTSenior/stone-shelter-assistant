"""Define structured selection and parsing responses for the search workflow."""

import re
from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool

from stone_shelter_assistant.assistant.candidate_evaluation import (
    CompatibilityCriterion,
    CriteriaGroup,
    HouseholdFact,
    QuotedCriterion,
    SearchCriteria,
)
from stone_shelter_assistant.assistant.question_grounding import GroundingProposal
from stone_shelter_assistant.assistant.ranking_policy import RANKING_POLICY
from stone_shelter_assistant.assistant.tool_planning import (
    ReferenceRequest,
    RequestedPair,
    RequestedPairList,
    StoneInfoTopic,
)
from stone_shelter_assistant.search.document_models import DEFAULT_LANGUAGE
from stone_shelter_assistant.search.enums import AccommodationFactType, CompatibilityVerdict
from stone_shelter_assistant.search.stones.search_contracts import StoneSearchFilters
from stone_shelter_assistant.stones.enums import AdoptionStatus, StoneType


class FragmentReference(BaseModel):
    fragment_id: int = Field(ge=1)


class HouseholdFactReference(FragmentReference):
    existing_stone_type: StoneType | None = None
    fact_type: AccommodationFactType | None = None
    value: StrictBool | None = None
    applies_to_pair: tuple[StoneType, StoneType] | None = None


class CompatibilityReference(FragmentReference):
    household_type: StoneType
    first_type: StoneType | None = None


class RequestedCompatibilityReference(CompatibilityReference):
    target: Literal["candidate", "named_stone", "types"]


class NamedStoneReference(FragmentReference):
    name: str = Field(min_length=1)


class CareReference(FragmentReference):
    stone_type: StoneType


class UnsupportedCareReference(FragmentReference):
    material: str = Field(min_length=1, max_length=120)


class StoneInfoReference(FragmentReference):
    topic: StoneInfoTopic


class PairListReference(FragmentReference):
    stone_type: StoneType
    verdict: CompatibilityVerdict


class CriteriaReferences(BaseModel):
    character: list[FragmentReference] = Field(default_factory=list)
    compatibility: list[CompatibilityReference] = Field(default_factory=list)

    def resolve(self, fragments: Mapping[int, str]) -> CriteriaGroup:
        return CriteriaGroup(
            character=[
                QuotedCriterion(
                    fragment_id=item.fragment_id, question_quote=fragments[item.fragment_id]
                )
                for item in self.character
            ],
            compatibility=[
                CompatibilityCriterion(
                    fragment_id=item.fragment_id,
                    question_quote=fragments[item.fragment_id],
                    household_type=item.household_type,
                )
                for item in self.compatibility
            ],
        )


class RetrievalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    lexical_query: str = Field(min_length=1)
    semantic_query: str = Field(min_length=1)
    filters: StoneSearchFilters


class CandidateTypeReference(FragmentReference):
    stone_type: StoneType


class RetrievalProposal(BaseModel):
    """The model proposes queries and a referenced type, never operational filters."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    lexical_query: str = Field(min_length=1)
    semantic_query: str = Field(min_length=1)
    candidate_type: CandidateTypeReference | None = None


class ParseQuestion(BaseModel):
    """Classify references to the original question without candidate data."""

    recommendation_limit: int = Field(ge=0)
    requested_availability: list[FragmentReference] = Field(default_factory=list)
    requested_compatibility: list[RequestedCompatibilityReference] = Field(default_factory=list)
    household_facts: list[HouseholdFactReference] = Field(default_factory=list)
    requirements: CriteriaReferences = Field(default_factory=CriteriaReferences)
    preferences: CriteriaReferences = Field(default_factory=CriteriaReferences)
    named_stone: NamedStoneReference | None = None
    recommendation_target: NamedStoneReference | None = None
    requested_care: list[CareReference] = Field(default_factory=list)
    unsupported_care: list[UnsupportedCareReference] = Field(default_factory=list)
    requested_stone_info: StoneInfoReference | None = None
    requested_pair_lists: list[PairListReference] = Field(default_factory=list)
    retrieval: RetrievalProposal | None = None

    def resolve_retrieval(
        self, fragments: Mapping[int, str], supported: frozenset[str] = frozenset()
    ) -> RetrievalRequest | None:
        if self.retrieval is None:
            return None
        proposal = self.retrieval
        stone_type = None
        if proposal.candidate_type is not None:
            candidate = proposal.candidate_type
            if "candidate_type" in supported:
                stone_type = candidate.stone_type
        return RetrievalRequest(
            lexical_query=proposal.lexical_query,
            semantic_query=proposal.semantic_query,
            filters=StoneSearchFilters(
                adoption_status=AdoptionStatus.AVAILABLE,
                language=DEFAULT_LANGUAGE,
                stone_type=stone_type,
            ),
        )

    def grounding_proposals(self, fragments: Mapping[int, str]) -> list[GroundingProposal]:
        proposals = [
            GroundingProposal(
                proposal_id=f"agreement:{index}",
                concept_id=fact.fact_type.value,
                fragment_id=fact.fragment_id,
                question_quote=fragments[fact.fragment_id],
                proposed_value=fact.value,
                applies_to_pair=fact.applies_to_pair,
            )
            for index, fact in enumerate(self.household_facts)
            if fact.fact_type is not None
        ]
        candidate = self.retrieval.candidate_type if self.retrieval else None
        if candidate is not None:
            proposals.append(
                GroundingProposal(
                    proposal_id="candidate_type",
                    concept_id="candidate_type",
                    fragment_id=candidate.fragment_id,
                    question_quote=fragments[candidate.fragment_id],
                    proposed_type=candidate.stone_type,
                )
            )
        return proposals

    def grounding_diagnostics(
        self, fragments: Mapping[int, str], supported: frozenset[str]
    ) -> list[dict[str, object]]:
        return [
            {
                "kind": "unsupported_candidate_type"
                if p.concept_id == "candidate_type"
                else "unsupported_agreement",
                **p.model_dump(mode="json"),
            }
            for p in self.grounding_proposals(fragments)
            if p.proposal_id not in supported
        ]

    def resolve_references(self, fragments: Mapping[int, str]) -> ReferenceRequest:
        name = None
        if self.named_stone is not None:
            name = self.named_stone.name.strip()
            if (
                not name
                or name.casefold() not in fragments[self.named_stone.fragment_id].casefold()
            ):
                raise ValueError("Stone name must occur in its question fragment")
        recommendation_name = None
        if self.recommendation_target is not None:
            if self.recommendation_target.fragment_id not in fragments:
                raise KeyError(self.recommendation_target.fragment_id)
            recommendation_name = self.recommendation_target.name.strip()
            if (
                not recommendation_name
                or recommendation_name.casefold()
                not in fragments[self.recommendation_target.fragment_id].casefold()
            ):
                raise ValueError("Recommendation name must occur in its question fragment")
        for item in [
            *self.requested_compatibility,
            *self.requested_care,
            *self.requested_pair_lists,
            *self.unsupported_care,
        ]:
            if item.fragment_id not in fragments:
                raise KeyError(item.fragment_id)
        for item in self.requested_compatibility:
            if item.target == "candidate":
                if item.first_type is not None or not self.recommendation_limit:
                    raise ValueError("Candidate compatibility needs an active recommendation")
            elif item.target == "named_stone":
                if item.first_type is not None or self.named_stone is None:
                    raise ValueError("Named-stone compatibility needs a named individual")
            elif item.first_type is None:
                raise ValueError("Type compatibility needs both explicit types")
        if self.requested_stone_info is not None:
            if self.requested_stone_info.fragment_id not in fragments:
                raise KeyError(self.requested_stone_info.fragment_id)
            if name is None:
                raise ValueError("A named stone is required for individual information")
        for unknown in self.unsupported_care:
            if unknown.material.casefold() not in fragments[unknown.fragment_id].casefold():
                raise ValueError("Unsupported material must occur in its question fragment")
            if unknown.material.upper() in StoneType.__members__:
                raise ValueError("Known materials must use requested_care")
        return ReferenceRequest(
            stone_name=name,
            recommendation_name=recommendation_name,
            stone_info=self.requested_stone_info.topic if self.requested_stone_info else None,
            unsupported_care=list(dict.fromkeys(item.material for item in self.unsupported_care)),
            care_types=list(dict.fromkeys(item.stone_type for item in self.requested_care)),
            pairs=[
                RequestedPair(first_type=first, second_type=second)
                for first, second in dict.fromkeys(
                    (item.first_type, item.household_type)
                    for item in self.requested_compatibility
                    if item.target in ("named_stone", "types")
                )
            ],
            pair_lists=[
                RequestedPairList(stone_type=kind, verdict=verdict)
                for kind, verdict in dict.fromkeys(
                    (item.stone_type, item.verdict) for item in self.requested_pair_lists
                )
            ],
        )

    def resolve(
        self, fragments: Mapping[int, str], supported: frozenset[str] = frozenset()
    ) -> tuple[SearchCriteria, int]:
        requirements = self.requirements.resolve(fragments)
        preferences = self.preferences.resolve(fragments)
        required_character = {item.fragment_id: item for item in requirements.character}
        required_compatibility = {
            (item.fragment_id, item.household_type): item for item in requirements.compatibility
        }
        preferred_character = {
            item.fragment_id: item
            for item in preferences.character
            if item.fragment_id not in required_character
        }
        preferred_compatibility = {
            (item.fragment_id, item.household_type): item
            for item in preferences.compatibility
            if (item.fragment_id, item.household_type) not in required_compatibility
        }
        duplicates_removed = (
            len(requirements.character)
            + len(requirements.compatibility)
            + len(preferences.character)
            + len(preferences.compatibility)
            - len(required_character)
            - len(required_compatibility)
            - len(preferred_character)
            - len(preferred_compatibility)
        )
        criteria = SearchCriteria(
            recommendation_limit=min(self.recommendation_limit, RANKING_POLICY.shortlist_limit),
            requested_availability=[
                QuotedCriterion(
                    fragment_id=item.fragment_id, question_quote=fragments[item.fragment_id]
                )
                for item in self.requested_availability
            ],
            requested_compatibility=[
                CompatibilityCriterion(
                    fragment_id=item.fragment_id,
                    question_quote=fragments[item.fragment_id],
                    household_type=item.household_type,
                )
                for item in self.requested_compatibility
                if item.target == "candidate"
            ],
            household_facts=[
                HouseholdFact(
                    question_quote=fragments[item.fragment_id],
                    **item.model_dump(),
                )
                for index, item in enumerate(self.household_facts)
                if item.fact_type is None or f"agreement:{index}" in supported
            ],
            requirements=CriteriaGroup(
                character=list(required_character.values()),
                compatibility=list(required_compatibility.values()),
            ),
            preferences=CriteriaGroup(
                character=list(preferred_character.values()),
                compatibility=list(preferred_compatibility.values()),
            ),
        )
        return criteria, duplicates_removed


class SelectCandidates(BaseModel):
    """Return candidate IDs from the retrieved cards in preference order."""

    model_config = ConfigDict(extra="forbid", strict=True)

    stone_ids: list[str]


def question_fragments(question: str) -> dict[int, str]:
    """Number verbatim clauses and lines, keeping punctuation and original language."""
    fragments = (part.strip() for part in re.split(r"(?<=[.!?;,:])\s+|\n+", question))
    return dict(enumerate((fragment for fragment in fragments if fragment), start=1))
