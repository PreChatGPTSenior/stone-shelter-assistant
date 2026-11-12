import json
from typing import Any

from tests.evaluation.scenario_stages import evaluate_scenario_record

POSITIVE = "stone-positive"
NEGATIVE = "stone-negative"


def _record() -> dict[str, Any]:
    return {
        "case_id": "Q-test",
        "response": {"answer": "Checked answer", "recommended_stone_ids": ["internal-positive"]},
        "graph_state": {
            "candidate_cards": {
                "internal-positive": {"external_id": POSITIVE},
                "internal-negative": {"external_id": NEGATIVE},
            },
            "retrieval_provenance": [
                {
                    "external_id": POSITIVE,
                    "lexical_rank": 2,
                    "semantic_rank": 1,
                    "rrf_score": 0.03,
                    "retrieval_rank": 1,
                    "in_pool": True,
                },
                {
                    "external_id": NEGATIVE,
                    "lexical_rank": 1,
                    "semantic_rank": None,
                    "rrf_score": 0.02,
                    "retrieval_rank": 2,
                    "in_pool": True,
                },
            ],
            "selected_stone_ids": ["internal-positive"],
            "candidate_evaluations": [
                {
                    "stone_id": "internal-positive",
                    "external_id": POSITIVE,
                    "reasons": [
                        {
                            "criterion": "quiet",
                            "evidence": [
                                {
                                    "source_id": "stone-card:internal-positive",
                                    "quote": "likes quiet",
                                }
                            ],
                        }
                    ],
                }
            ],
            "evaluation_sources": {},
            "recommended_stone_ids": ["internal-positive"],
            "result": {
                "recommended_stone_ids": ["internal-positive"],
                "candidate_decisions": [
                    {"stone_id": "internal-positive", "outcome": "recommended"}
                ],
                "answer": "Checked answer",
                "sources": {},
            },
        },
    }


def _targets(**overrides: object) -> dict[str, Any]:
    result: dict[str, object] = {
        "stage_applicability": "recommendation",
        "positive_retrieval_external_ids": [POSITIVE],
        "counterexample_external_ids": [NEGATIVE],
        "filter_ineligible_external_ids": [],
    }
    result.update(overrides)
    return result


def test_stage_report_tracks_real_ids_rank_and_loss_without_collapsing_stages() -> None:
    report = evaluate_scenario_record(_record(), _targets())
    stages = {item["stage"]: item for item in report["stages"]}
    assert stages["lexical"]["actual_external_ids"] == [NEGATIVE, POSITIVE]
    assert stages["semantic"]["actual_external_ids"] == [POSITIVE]
    assert stages["rrf"]["actual_external_ids"] == [POSITIVE, NEGATIVE]
    assert stages["shortlist"]["actual_external_ids"] == [POSITIVE]
    assert stages["evidence"]["actual_external_ids"] == [POSITIVE]
    assert stages["decision"]["actual_external_ids"] == [POSITIVE]
    assert stages["answer"]["actual_external_ids"] == [POSITIVE]
    assert stages["lexical"]["status"] == "pass"
    assert stages["semantic"]["status"] == "pass"
    assert stages["evidence"]["positive_found"] == [POSITIVE]
    assert stages["shortlist"]["lost_from_previous_stage"] == []
    assert report["engine_ranks"][POSITIVE] == {
        "lexical_rank": 2,
        "semantic_rank": 1,
        "rrf_score": 0.03,
        "retrieval_rank": 1,
        "in_pool": True,
    }
    assert report["counterexamples"]["status"] == "not_evaluated"
    assert report["semantic_answer_assessment"]["status"] == "unmeasured"


def test_empty_results_cannot_pass_only_by_omitting_a_counterexample() -> None:
    report = evaluate_scenario_record(
        {
            "case_id": "Q-negative",
            "graph_state": {
                "retrieval_provenance": [],
                "selected_stone_ids": [],
                "candidate_evaluations": [],
                "evaluation_sources": {},
                "recommended_stone_ids": [],
                "candidate_cards": {},
                "result": {"recommended_stone_ids": [], "candidate_decisions": [], "answer": ""},
            },
        },
        _targets(positive_retrieval_external_ids=[POSITIVE]),
    )
    stages = {item["stage"]: item for item in report["stages"]}
    assert stages["lexical"]["status"] == "fail"
    assert stages["decision"]["status"] == "fail"
    assert report["counterexamples"]["status"] == "not_evaluated"
    assert report["counterexamples"]["does_not_establish_positive_coverage"] is True


def test_missing_stage_state_and_technical_errors_remain_unknown() -> None:
    report = evaluate_scenario_record(
        {"case_id": "Q-error", "technical_error": "TimeoutError", "graph_state": {}},
        _targets(),
    )
    assert {item["status"] for item in report["stages"]} == {"unknown"}
    assert report["technical_error"] == "TimeoutError"


def test_reference_and_unsupported_comparison_have_distinct_stage_semantics() -> None:
    base = _record()
    reference = evaluate_scenario_record(
        base,
        _targets(
            stage_applicability="not_applicable",
            positive_retrieval_external_ids=[],
            counterexample_external_ids=[],
        ),
    )
    unsupported = evaluate_scenario_record(
        base,
        _targets(
            stage_applicability="unsupported_capability",
            positive_retrieval_external_ids=[POSITIVE],
            counterexample_external_ids=[],
        ),
    )
    assert {item["status"] for item in reference["stages"]} == {"not_applicable"}
    assert {item["status"] for item in unsupported["stages"]} == {"capability_unverified"}


def test_filter_ineligible_target_is_separate_from_recall() -> None:
    report = evaluate_scenario_record(
        {
            "case_id": "Q-filter",
            "graph_state": {
                "retrieval_provenance": [],
                "selected_stone_ids": [],
                "candidate_evaluations": [],
                "evaluation_sources": {},
                "recommended_stone_ids": [],
                "candidate_cards": {},
                "result": {"recommended_stone_ids": [], "candidate_decisions": [], "answer": ""},
            },
        },
        _targets(
            stage_applicability="recommendation_filter_only",
            positive_retrieval_external_ids=[],
            counterexample_external_ids=[],
            filter_ineligible_external_ids=[NEGATIVE],
        ),
    )
    assert {item["status"] for item in report["stages"]} == {"not_applicable"}
    assert report["filter_ineligible_targets"]["status"] == "reported_separately_from_recall"


def test_execution_integrity_flags_http_success_with_invalid_plan() -> None:
    record = _record()
    record["graph_state"]["plan_status"] = "invalid_plan"
    report = evaluate_scenario_record(record, _targets())
    assert report["workflow_integrity"]["status"] == "fail"
    assert report["workflow_integrity"]["plan_status"] == "invalid_plan"


def test_mixed_reference_answer_does_not_hide_blocked_recommendation_coverage() -> None:
    record = _record()
    graph = record["graph_state"]
    graph.update(
        criteria_status="parsed",
        plan_status="accepted",
        question_coverage_status="incomplete",
        parsed_question={"recommendation_limit": 1},
        permitted_tools=["get_stone_details"],
        blocked_tools=["search_candidates"],
    )
    graph["result"].update(
        recommendation_status="blocked_question_coverage",
        answer="Svetlana's profile is available. No recommendation was made.",
        recommended_stone_ids=[],
        candidate_decisions=[],
    )
    record["response"] = graph["result"]
    report = evaluate_scenario_record(record, _targets())
    assert report["workflow_integrity"]["status"] == "pass"
    assert report["workflow_integrity"]["question_coverage_status"] == "incomplete"
    assert report["recommendations"]["coverage_gate"] == {
        "status": "blocked_incomplete_coverage",
        "coverage_status": "incomplete",
    }


def test_evaluate_run_emits_unknown_for_selected_case_missing_from_archive() -> None:
    from tests.evaluation.scenario_stages import evaluate_run

    report = evaluate_run(
        {"selected_case_ids": ["Q-missing"], "records": []},
        {"scenarios": {"Q-missing": _targets()}},
    )
    missing = report["scenario_reports"][0]
    assert missing["technical_error"] == "missing_case_record"
    assert {stage["status"] for stage in missing["stages"]} == {"unknown"}
    assert missing["counterexamples"]["status"] == "unknown"


def test_q09_style_retrieval_without_shortlist_is_not_an_exclusion_success() -> None:
    madame = "madame-external"
    record = {
        "case_id": "Q09",
        "graph_state": {
            "plan_status": "accepted",
            "criteria_status": "parsed",
            "assessment_status": "not_needed",
            "retrieval_provenance": [
                {
                    "external_id": madame,
                    "lexical_rank": 1,
                    "semantic_rank": 1,
                    "retrieval_rank": 1,
                    "in_pool": True,
                    "rrf_score": 0.03,
                }
            ],
            "selected_stone_ids": [],
            "candidate_cards": {},
            "candidate_evaluations": [],
            "evaluation_sources": {},
            "recommended_stone_ids": [],
            "result": {
                "candidate_decisions": [],
                "recommended_stone_ids": [],
                "answer": "No candidate passed selection.",
            },
        },
    }
    report = evaluate_scenario_record(
        record,
        _targets(
            positive_retrieval_external_ids=[madame],
            counterexample_external_ids=[madame],
            expected_dispositions={madame: "excluded"},
            expected_dispositions_when_evaluated=True,
        ),
    )
    stages = {item["stage"]: item for item in report["stages"]}
    assert stages["rrf"]["status"] == "pass"
    assert stages["shortlist"]["status"] == "fail"
    assert report["counterexamples"]["status"] == "not_evaluated"
    assert report["recommendations"]["disposition_check"]["status"] == "not_evaluated"


def test_target_config_covers_manifest_and_uses_only_stable_external_ids() -> None:
    import json
    from pathlib import Path

    root = Path(__file__).parents[2]
    suite = root / "tests/fixtures/agent-eval/questions-challenge-20"
    manifest = json.loads((suite / "scenarios.json").read_text())
    targets = json.loads((suite / "scenario-evaluation-targets.json").read_text())
    scenario_ids = {case["id"] for case in manifest["scenarios"]}
    external_ids = {stone["external_id"] for stone in manifest["stones"]}
    assert set(targets["scenarios"]) == scenario_ids
    for config in targets["scenarios"].values():
        fields = (
            "positive_retrieval_external_ids",
            "counterexample_external_ids",
            "filter_ineligible_external_ids",
            "comparison_external_ids",
        )
        for field in fields:
            values = config.get(field, [])
            assert len(values) == len(set(values))
            assert set(values) <= external_ids
        assert set(config.get("expected_dispositions", {})) <= external_ids
    assert targets["scenarios"]["Q11"]["filter_ineligible_external_ids"]
    assert targets["scenarios"]["Q18"]["stage_applicability"] == "unsupported_capability"


def test_decision_and_answer_stages_measure_considered_candidates_separately_from_recs() -> None:
    record = _record()
    graph = record["graph_state"]
    graph["retrieval_provenance"][1]["in_pool"] = True
    graph["candidate_evaluations"][0]["outcome"] = "recommended"
    graph["candidate_evaluations"].append(
        {
            "stone_id": "internal-negative",
            "external_id": NEGATIVE,
            "outcome": "conditional_option",
            "reasons": [],
        }
    )
    graph["result"]["candidate_decisions"] = [
        {"stone_id": "internal-positive", "outcome": "recommended"},
        {"stone_id": "internal-negative", "outcome": "conditional_option"},
    ]
    report = evaluate_scenario_record(record, _targets())
    stages = {item["stage"]: item for item in report["stages"]}
    assert stages["decision"]["actual_external_ids"] == [POSITIVE, NEGATIVE]
    assert stages["answer"]["actual_external_ids"] == [POSITIVE, NEGATIVE]
    assert report["recommendations"]["external_ids"] == [POSITIVE]


def test_source_binding_and_explicit_condition_outcomes_are_separate_checks() -> None:
    record = _record()
    record["expected"] = {
        "condition_checks": {"pair_key": "GRANITE+GRANITE", "rotate_decisions": "confirmed"}
    }
    evaluation = record["graph_state"]["candidate_evaluations"][0]
    evaluation["reasons"][0]["criterion"] = "compatibility"
    evaluation["reasons"][0]["pair_key"] = "GRANITE+GRANITE"
    evaluation["reasons"][0]["condition_checks"] = [
        {"condition_id": "rotate_decisions", "status": "unknown"}
    ]
    report = evaluate_scenario_record(record, _targets())
    assert report["structured_expectations"]["status"] == "fail"
    assert report["structured_expectations"]["checks"][
        "condition:GRANITE+GRANITE:rotate_decisions"
    ] == {
        "expected": "confirmed",
        "actual": "unknown",
        "status": "fail",
    }


def test_named_lexical_route_uses_search_document_external_id_and_skips_rrf() -> None:
    external = "named-external"
    record = {
        "case_id": "Q-named",
        "graph_state": {
            "reference_request": {"recommendation_name": "Madame"},
            "messages": [
                {
                    "type": "tool",
                    "name": "search_stones_lexical",
                    "content": json.dumps(
                        [{"id": "internal", "stone_external_id": external, "title": "Madame"}]
                    ),
                }
            ],
            "candidate_cards": {"internal": {"external_id": external}},
            "selected_stone_ids": ["internal"],
            "candidate_evaluations": [],
            "evaluation_sources": {},
            "result": {"candidate_decisions": [], "answer": "No verified recommendation."},
        },
    }
    report = evaluate_scenario_record(
        record,
        _targets(
            positive_retrieval_external_ids=[external],
            counterexample_external_ids=[],
        ),
    )
    stages = {item["stage"]: item for item in report["stages"]}
    assert stages["lexical"]["actual_external_ids"] == [external]
    assert stages["semantic"]["status"] == "not_applicable"
    assert stages["rrf"]["status"] == "not_applicable"


def test_rrf_dropped_targets_are_losses_from_parallel_engine_union() -> None:
    record = _record()
    record["graph_state"]["retrieval_provenance"][0]["in_pool"] = False
    report = evaluate_scenario_record(record, _targets())
    stages = {item["stage"]: item for item in report["stages"]}
    assert POSITIVE in stages["engine_union"]["actual_external_ids"]
    assert POSITIVE not in stages["rrf"]["actual_external_ids"]
    assert stages["rrf"]["lost_from_previous_stage"] == [POSITIVE]


def test_pair_evidence_with_authoritative_reason_source_needs_no_quote() -> None:
    record = _record()
    candidate = record["graph_state"]["candidate_evaluations"][0]
    candidate["reasons"].append(
        {"criterion": "compatibility", "source_id": "pair:granite+obsidian", "evidence": []}
    )
    record["graph_state"]["evaluation_sources"]["pair:granite+obsidian"] = {
        "tool": "exact_pair",
        "data": {"pair_key": "GRANITE+OBSIDIAN", "verdict": "HARMONIOUS"},
    }
    report = evaluate_scenario_record(record, _targets())
    assert (
        POSITIVE
        in next(stage for stage in report["stages"] if stage["stage"] == "evidence")[
            "actual_external_ids"
        ]
    )
    assert any(
        ref["source_id"] == "pair:granite+obsidian" and ref["source_present"]
        for ref in report["evidence_detail"][POSITIVE]
    )


def test_condition_check_ids_are_scoped_to_the_expected_pair() -> None:
    record = _record()
    record["expected"] = {
        "condition_checks": {"pair_key": "GRANITE+GRANITE", "rotate_decisions": "unknown"}
    }
    evaluation = record["graph_state"]["candidate_evaluations"][0]
    evaluation["reasons"] = [
        {
            "criterion": "compatibility",
            "pair_key": "BASALT+GNEISS",
            "condition_checks": [{"condition_id": "rotate_decisions", "status": "confirmed"}],
        },
        {
            "criterion": "compatibility",
            "pair_key": "GRANITE+GRANITE",
            "condition_checks": [{"condition_id": "rotate_decisions", "status": "unknown"}],
        },
    ]
    report = evaluate_scenario_record(record, _targets())
    check = report["structured_expectations"]["checks"][
        "condition:GRANITE+GRANITE:rotate_decisions"
    ]
    assert check["actual"] == "unknown"
    assert check["status"] == "pass"


def test_archive_duplicates_and_unknown_target_configs_are_reported_as_unknown() -> None:
    from tests.evaluation.scenario_stages import evaluate_run

    targets = {"scenarios": {"Q-test": _targets()}}
    graph_record = _record()
    graph_record["case_id"] = "Q-test"
    report = evaluate_run(
        {
            "selected_case_ids": ["Q-test", "Q-unconfigured"],
            "records": [graph_record, graph_record],
        },
        targets,
    )
    assert report["archive_integrity"]["duplicate_case_record_ids"] == ["Q-test"]
    assert report["archive_integrity"]["selected_cases_missing_target_config"] == ["Q-unconfigured"]
    assert report["scenario_reports"][0]["technical_error"] == "duplicate_case_records"
    assert report["scenario_reports"][1]["technical_error"] == "missing_target_configuration"
