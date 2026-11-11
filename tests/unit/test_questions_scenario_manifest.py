"""Validate the future evaluation corpus without calling models or databases."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUITE = ROOT / "tests/fixtures/agent-eval/questions-challenge-20/scenarios.json"


def test_scenarios_cover_every_authored_stone_without_stale_operational_facts() -> None:
    suite = json.loads(SUITE.read_text())
    fixtures = [json.loads(path.read_text()) for path in (ROOT / "fixtures/stones").glob("*.json")]
    cards = {item["stone"]["externalId"]: item for item in fixtures}
    assert len(cards) == len(suite["stones"]) == 10
    assert {stone["external_id"] for stone in suite["stones"]} == set(cards)
    for stone in suite["stones"]:
        card = cards[stone["external_id"]]
        assert json.loads((ROOT / stone["fixture"]).read_text()) == card
        assert stone["name"] == card["stone"]["name"]
        assert stone["stone_type"] == card["stone"]["stoneType"]
        assert stone["status"] == card["shelterCase"]["adoptionStatus"]
    scenarios = suite["scenarios"]
    assert len(scenarios) == 20
    assert len({scenario["id"] for scenario in scenarios}) == 20
    assert len({scenario["question"] for scenario in scenarios}) == 20
    assert {sid for scenario in scenarios for sid in scenario["focus_stone_ids"]} == set(cards)
    for scenario in scenarios:
        assert scenario["expected"]["required"]
        assert scenario["expected"]["forbidden"]
        assert scenario["execution_status"] == "not_run"
        assert all((ROOT / source["file"]).is_file() for source in scenario["evidence"])


def test_scenario_pair_expectations_match_authored_rules() -> None:
    suite = json.loads(SUITE.read_text())
    knowledge = json.loads((ROOT / suite["knowledge_sources"]["compatibility"]).read_text())
    pairs = {"+".join(sorted(pair["stone_types"])): pair for pair in knowledge["pairings"]}
    for scenario in suite["scenarios"]:
        expected = scenario["expected"]
        if pair := expected.get("pair"):
            assert pair["verdict"] == pairs[pair["key"]]["verdict"]
        if checks := expected.get("condition_checks"):
            rule = pairs[checks["pair_key"]]
            assert set(checks) - {"pair_key"} == {condition["id"] for condition in rule["conditions"]}


def test_existing_questions_are_preserved_in_the_new_suite() -> None:
    suite = json.loads(SUITE.read_text())
    scenarios = {scenario["id"]: scenario for scenario in suite["scenarios"]}
    assert sum(s["origin"] == "existing_baseline" for s in scenarios.values()) == 3
    for scenario_id in ("Q02", "Q03"):
        scenario = scenarios[scenario_id]
        archived = json.loads((ROOT / scenario["baseline_reference"] / "input.json").read_text())
        assert scenario["question"] == archived["question"]
    assert scenarios["Q01"]["question"] in (ROOT / "docs/setup.md").read_text()
