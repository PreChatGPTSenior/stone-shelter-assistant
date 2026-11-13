"""Typed parsed criteria used to assess stone candidates."""

from dataclasses import dataclass
from typing import Self

from pydantic import BaseModel, Field, StrictBool, model_validator

from stone_shelter_assistant.assistant.ranking_policy import RANKING_POLICY
from stone_shelter_assistant.search.enums import AccommodationFactType
from stone_shelter_assistant.stones.enums import StoneType


class QuotedCriterion(BaseModel):
    criterion_id: str = Field(min_length=1)
    fragment_id: int = Field(ge=1)
    question_quote: str = Field(min_length=1)


class HouseholdFact(QuotedCriterion):
    existing_stone_type: StoneType | None = None
    fact_type: AccommodationFactType | None = None
    value: StrictBool | None = None
    applies_to_pair: tuple[StoneType, StoneType] | None = None

    @model_validator(mode="after")
    def validate_accommodation_fact(self) -> Self:
        if self.fact_type is None:
            if self.value is not None or self.applies_to_pair is not None:
                raise ValueError("Accommodation values and pair scope require a fact type")
        elif self.value is None or self.existing_stone_type is not None:
            raise ValueError(
                "An accommodation fact requires a boolean and cannot assert a stone type"
            )
        return self


class CompatibilityCriterion(QuotedCriterion):
    household_type: StoneType


class CriteriaGroup(BaseModel):
    character: list[QuotedCriterion]
    compatibility: list[CompatibilityCriterion]


@dataclass(frozen=True)
class CompatibilityTarget:
    quote: str
    required: bool
    existing_household: bool
    lookup_only: bool = False


class SearchCriteria(BaseModel):
    recommendation_limit: int = Field(ge=0, le=RANKING_POLICY.shortlist_limit)
    requested_availability: list[QuotedCriterion] = Field(default_factory=list)
    requested_compatibility: list[CompatibilityCriterion] = Field(default_factory=list)
    household_facts: list[HouseholdFact]
    requirements: CriteriaGroup
    preferences: CriteriaGroup

    def compatibility_targets(self) -> dict[StoneType, CompatibilityTarget]:
        """Check explicit pair criteria and types already living in the household."""
        facts = {
            fact.existing_stone_type: fact.question_quote
            for fact in self.household_facts
            if fact.existing_stone_type is not None
        }
        groups = {
            "household_fact": list(facts.items()),
            "preference": [
                (item.household_type, item.question_quote)
                for item in self.preferences.compatibility
            ],
            "requirement": [
                (item.household_type, item.question_quote)
                for item in self.requirements.compatibility
            ],
        }
        required_types = {item.household_type for item in self.requirements.compatibility}
        targets: dict[StoneType, CompatibilityTarget] = {}
        for group in sorted(
            RANKING_POLICY.target_priority, key=RANKING_POLICY.target_priority.__getitem__
        ):
            for stone_type, quote in groups[group]:
                targets.setdefault(
                    stone_type,
                    CompatibilityTarget(quote, stone_type in required_types, stone_type in facts),
                )
        for item in self.requested_compatibility:
            targets.setdefault(
                item.household_type,
                CompatibilityTarget(
                    item.question_quote, required=False, existing_household=False, lookup_only=True
                ),
            )
        return targets
