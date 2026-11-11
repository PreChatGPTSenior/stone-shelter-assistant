"""Define structured selection and parsing responses for the search workflow."""

import re
from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field, StrictBool

from stone_shelter_assistant.assistant.candidate_evaluation import (
    CompatibilityCriterion,
    CriteriaGroup,
    HouseholdFact,
    QuotedCriterion,
    SearchCriteria,
)
from stone_shelter_assistant.assistant.ranking_policy import RANKING_POLICY
from stone_shelter_assistant.assistant.tool_planning import (
    ReferenceRequest,
    RequestedPair,
    RequestedPairList,
)
from stone_shelter_assistant.search.enums import AccommodationFactType, CompatibilityVerdict
from stone_shelter_assistant.stones.enums import StoneType


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


class NamedStoneReference(FragmentReference):
    name: str = Field(min_length=1)


class CareReference(FragmentReference):
    stone_type: StoneType


class PairListReference(FragmentReference):
    stone_type: StoneType
    verdict: CompatibilityVerdict


class CriteriaReferences(BaseModel):
    character: list[FragmentReference]
    compatibility: list[CompatibilityReference]

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


class ParseQuestion(BaseModel):
    """Classify references to the original question without candidate data."""

    recommendation_limit: int = Field(ge=0)
    requested_availability: list[FragmentReference]
    requested_compatibility: list[CompatibilityReference]
    household_facts: list[HouseholdFactReference]
    requirements: CriteriaReferences
    preferences: CriteriaReferences
    named_stone: NamedStoneReference | None = None
    requested_care: list[CareReference] = Field(default_factory=list)
    requested_pair_lists: list[PairListReference] = Field(default_factory=list)

    def resolve_references(self, fragments: Mapping[int, str]) -> ReferenceRequest:
        name = None
        if self.named_stone is not None:
            name = self.named_stone.name.strip()
            if (
                not name
                or name.casefold() not in fragments[self.named_stone.fragment_id].casefold()
            ):
                raise ValueError("Stone name must occur in its question fragment")
        for item in [*self.requested_care, *self.requested_pair_lists]:
            if item.fragment_id not in fragments:
                raise KeyError(item.fragment_id)
        return ReferenceRequest(
            stone_name=name,
            care_types=list(dict.fromkeys(item.stone_type for item in self.requested_care)),
            pairs=[
                RequestedPair(first_type=first, second_type=second)
                for first, second in dict.fromkeys(
                    (item.first_type, item.household_type) for item in self.requested_compatibility
                )
            ],
            pair_lists=[
                RequestedPairList(stone_type=kind, verdict=verdict)
                for kind, verdict in dict.fromkeys(
                    (item.stone_type, item.verdict) for item in self.requested_pair_lists
                )
            ],
        )

    def resolve(self, fragments: Mapping[int, str]) -> tuple[SearchCriteria, int]:
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
            ],
            household_facts=[
                HouseholdFact(
                    question_quote=fragments[item.fragment_id],
                    **item.model_dump(),
                )
                for item in self.household_facts
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
