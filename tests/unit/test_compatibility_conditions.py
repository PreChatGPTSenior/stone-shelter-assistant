import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from stone_shelter_assistant.assistant.candidate_evaluation import (
    AssessedEvidence,
    CandidateEvidence,
    CompatibilityTarget,
    HouseholdFact,
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
ARCHIVE = ROOT / "tests/fixtures/agent-eval/quiet-home-with-granite"


@pytest.fixture
def granite_pair() -> CompatibilityPairSearchDocument:
    documents = build_stone_compatibility_documents(
        (ROOT / SOURCE).read_text(), SOURCE.as_posix()
    )
    return next(
        pair
        for pair in documents
        if isinstance(pair, CompatibilityPairSearchDocument) and pair.pair_key == "GRANITE+GRANITE"
    )


def agreement(kind: AccommodationFactType, value: bool = True) -> HouseholdFact:
    return HouseholdFact(
        fragment_id=2,
        question_quote="We have agreed on these household arrangements.",
        fact_type=kind,
        value=value,
    )


def test_archived_claude_quote_and_fragment_no_longer_confirm_conditions(
    granite_pair: CompatibilityPairSearchDocument,
) -> None:
    run = json.loads((ARCHIVE / "runs/2026-11-11-8192.json").read_text())
    output = next(row for row in run["attempts"] if row["model_id"] == "anthropic/claude-sonnet-5")
    legacy = AssessedEvidence.model_validate(output["assessment"])
    assert legacy.accommodations
    fact = HouseholdFact(
        fragment_id=2, question_quote="где уже есть гранит.", existing_stone_type=StoneType.GRANITE
    )
    reason = compatibility_reason(
        stone_id="granite-stone",
        key=granite_pair.pair_key,
        target=CompatibilityTarget(fact.question_quote, required=False, existing_household=True),
        pair=granite_pair,
        facts=[fact],
        sources={},
        assessment=legacy,
    )
    assert reason.verdict == CompatibilityVerdict.CONDITIONAL
    assert reason.policy_rule == "conditions_unconfirmed"
    assert reason.conditions_status == "unconfirmed"
    assert all(check.status == "unknown" for check in reason.condition_checks)


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
                {"fragment_id": 1, "existing_stone_type": "GRANITE"},
                {"fragment_id": 2, "fact_type": "decision_rotation_agreed", "value": True},
                {"fragment_id": 3, "fact_type": "decision_deadline_agreed", "value": True},
            ],
            "requirements": {"character": [], "compatibility": []},
            "preferences": {"character": [], "compatibility": []},
        }
    )
    criteria, _ = parsed.resolve(fragments)
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
        HouseholdFact(fragment_id=1, question_quote="Granite is here", value=True)
    with pytest.raises(ValidationError):
        HouseholdFact(
            fragment_id=1,
            question_quote="Granite is here",
            fact_type=AccommodationFactType.DECISION_ROTATION_AGREED,
            existing_stone_type=StoneType.GRANITE,
            value=True,
        )


def test_archived_schema_is_preserved_but_current_model_dto_has_no_accommodations() -> None:
    snapshot = json.loads((ARCHIVE / "input.json").read_text())
    assert snapshot["schema"] == AssessedEvidence.model_json_schema()
    assert "accommodations" not in CandidateEvidence.model_json_schema()["properties"]
