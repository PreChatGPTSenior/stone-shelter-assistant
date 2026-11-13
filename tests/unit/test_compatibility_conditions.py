from pathlib import Path

import pytest
from pydantic import ValidationError

from stone_shelter_assistant.assistant.candidate_evaluation import (
    CandidateEvidence,
    CompatibilityTarget,
    CriteriaGroup,
    HouseholdFact,
    SearchCriteria,
    check_pair_conditions,
    compatibility_reason,
)
from stone_shelter_assistant.assistant.selection import ParseQuestion
from stone_shelter_assistant.search.document_models import CompatibilityPairSearchDocument
from stone_shelter_assistant.search.enums import AccommodationFactType, CompatibilityVerdict
from stone_shelter_assistant.search.knowledge.stone_compatibility_document_builder import (
    build_stone_compatibility_documents,
)
from stone_shelter_assistant.stones.enums import StoneType

ROOT = Path(__file__).parents[2]
SOURCE = Path("fixtures/knowledge/type-compatibility/stone-type-compatibility_en.json")


@pytest.fixture
def granite_pair() -> CompatibilityPairSearchDocument:
    documents = build_stone_compatibility_documents((ROOT / SOURCE).read_text(), SOURCE.as_posix())
    return next(
        pair
        for pair in documents
        if isinstance(pair, CompatibilityPairSearchDocument) and pair.pair_key == "GRANITE+GRANITE"
    )


def agreement(kind: AccommodationFactType, value: bool = True) -> HouseholdFact:
    return HouseholdFact(
        criterion_id=f"test.fact.{kind.value}",
        fragment_id=2,
        question_quote="We have agreed on these household arrangements.",
        fact_type=kind,
        value=value,
    )


def test_existing_granite_does_not_confirm_household_agreements(
    granite_pair: CompatibilityPairSearchDocument,
) -> None:
    fact = HouseholdFact(
        criterion_id="household_fact.1",
        fragment_id=2,
        question_quote="where granite already lives.",
        existing_stone_type=StoneType.GRANITE,
    )
    reason = compatibility_reason(
        stone_id="granite-stone",
        key=granite_pair.pair_key,
        target=CompatibilityTarget(fact.question_quote, required=False, existing_household=True),
        pair=granite_pair,
        facts=[fact],
        sources={},
        assessment=CandidateEvidence(character=[], individual_compatibility=[]),
    )
    assert reason.verdict == CompatibilityVerdict.CONDITIONAL
    assert reason.policy_rule == "conditions_unconfirmed"
    assert reason.conditions_status == "unconfirmed"
    criteria = SearchCriteria(
        recommendation_limit=1,
        household_facts=[fact],
        requirements=CriteriaGroup(character=[], compatibility=[]),
        preferences=CriteriaGroup(character=[], compatibility=[]),
    )
    assert criteria.compatibility_targets()[StoneType.GRANITE].required is False
    assert all(check.status == "unknown" for check in reason.condition_checks)


def test_explicit_hard_compatibility_requirement_remains_mandatory() -> None:
    question = "Find a candidate who must live well with the granite already at home."
    parsed = ParseQuestion.model_validate(
        {
            "recommendation_limit": 1,
            "household_facts": [
                {
                    "fragment_id": 1,
                    "question_quote": "the granite already at home",
                    "existing_stone_type": "GRANITE",
                }
            ],
            "requirements": {
                "character": [],
                "compatibility": [
                    {
                        "fragment_id": 1,
                        "household_type": "GRANITE",
                        "question_quote": "must live well with the granite already at home",
                    }
                ],
            },
            "preferences": {"character": [], "compatibility": []},
        }
    )
    criteria, _ = parsed.resolve({1: question})

    assert criteria.compatibility_targets()[StoneType.GRANITE].required is True


def test_parser_restores_typed_fact_quotes_and_all_conditions_are_required(
    granite_pair: CompatibilityPairSearchDocument,
) -> None:
    fragments = {
        1: "There is already granite at home.",
        2: "We agreed to take turns on small decisions.",
        3: "We established a deadline for shared decisions.",
    }
    parsed = ParseQuestion.model_validate(
        {
            "recommendation_limit": 2,
            "requested_availability": [],
            "requested_compatibility": [],
            "household_facts": [
                {"fragment_id": 1, "question_quote": fragments[1], "existing_stone_type": "GRANITE"},
                {"fragment_id": 2, "question_quote": fragments[2], "fact_type": "decision_rotation_agreed", "value": True},
                {"fragment_id": 3, "question_quote": fragments[3], "fact_type": "decision_deadline_agreed", "value": True},
            ],
            "requirements": {"character": [], "compatibility": []},
            "preferences": {"character": [], "compatibility": []},
        }
    )
    criteria, _ = parsed.resolve(fragments, frozenset({"agreement:1", "agreement:2"}))
    assert [fact.question_quote for fact in criteria.household_facts] == list(fragments.values())
    assert set(criteria.compatibility_targets()) == {StoneType.GRANITE}
    assert [
        check.status for check in check_pair_conditions(granite_pair, criteria.household_facts)
    ] == ["confirmed", "confirmed"]
    partial = check_pair_conditions(granite_pair, criteria.household_facts[:2])
    assert [check.status for check in partial] == ["confirmed", "unknown"]
    reason = compatibility_reason(
        stone_id="granite-stone",
        key=granite_pair.pair_key,
        target=criteria.compatibility_targets()[StoneType.GRANITE],
        pair=granite_pair,
        facts=criteria.household_facts,
        sources={},
        assessment=CandidateEvidence(character=[], individual_compatibility=[]),
    )
    assert reason.policy_rule == "conditions_confirmed"
    assert reason.base_score == 0.75


def test_unmarked_pair_stays_conditional_with_typed_agreements(
    granite_pair: CompatibilityPairSearchDocument,
) -> None:
    old_document = granite_pair.model_dump(exclude={"conditions"})
    unmarked = CompatibilityPairSearchDocument.model_validate(old_document)
    facts = [agreement(kind) for kind in AccommodationFactType]
    reason = compatibility_reason(
        stone_id="granite-stone",
        key=unmarked.pair_key,
        target=CompatibilityTarget("Existing granite", required=False, existing_household=True),
        pair=unmarked,
        facts=facts,
        sources={},
        assessment=CandidateEvidence(character=[], individual_compatibility=[]),
    )
    assert reason.policy_rule == "conditions_unconfirmed"
    assert reason.conditions_status == "unmarked"


def test_denials_conflicts_and_other_pair_scopes_do_not_confirm_conditions(
    granite_pair: CompatibilityPairSearchDocument,
) -> None:
    kind = AccommodationFactType.DECISION_ROTATION_AGREED
    assert check_pair_conditions(granite_pair, [agreement(kind, False)])[0].status == "contradicted"
    assert (
        check_pair_conditions(granite_pair, [agreement(kind), agreement(kind, False)])[0].status
        == "conflict"
    )
    other_pair = agreement(kind).model_copy(
        update={"applies_to_pair": (StoneType.GRANITE, StoneType.OBSIDIAN)}
    )
    assert check_pair_conditions(granite_pair, [other_pair])[0].status == "unknown"


def test_invalid_rule_quote_does_not_confirm_condition(
    granite_pair: CompatibilityPairSearchDocument,
) -> None:
    invalid = granite_pair.conditions[0].model_copy(update={"source_quote": "An invented rule"})
    pair = granite_pair.model_copy(update={"conditions": [invalid]})
    assert check_pair_conditions(pair, [agreement(invalid.fact_type)])[0].status == "invalid_rule"


def test_typed_fact_requires_its_own_boolean_value() -> None:
    with pytest.raises(ValidationError):
        HouseholdFact(
            criterion_id="test.invalid.1",
            fragment_id=1,
            question_quote="Granite is here",
            value=True,
        )
    with pytest.raises(ValidationError):
        HouseholdFact(
            criterion_id="test.invalid.2",
            fragment_id=1,
            question_quote="Granite is here",
            fact_type=AccommodationFactType.DECISION_ROTATION_AGREED,
            existing_stone_type=StoneType.GRANITE,
            value=True,
        )


def test_current_model_dto_rejects_accommodation_verdicts() -> None:
    with pytest.raises(ValidationError):
        CandidateEvidence.model_validate(
            {"character": [], "individual_compatibility": [], "accommodations": []}
        )
    assert "accommodations" not in CandidateEvidence.model_json_schema()["properties"]
