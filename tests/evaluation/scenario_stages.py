"""Pure stage-loss report for archived challenge-run records."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

STAGES = (
    "lexical",
    "semantic",
    "engine_union",
    "rrf",
    "shortlist",
    "evidence",
    "decision",
    "answer",
)


def _unique(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _to_external(ids: Sequence[Any], internal_to_external: Mapping[str, str]) -> list[str]:
    return _unique(
        [
            internal_to_external[value]
            for value in ids
            if isinstance(value, str) and value in internal_to_external
        ]
    )


def _unmapped_ids(ids: Sequence[Any], internal_to_external: Mapping[str, str]) -> list[str]:
    return _unique(
        [value for value in ids if isinstance(value, str) and value not in internal_to_external]
    )


def _target_stage(
    stage: str,
    actual_ids: list[str],
    positive_targets: list[str],
    previous_ids: list[str] | None,
    *,
    unavailable_reason: str | None = None,
) -> dict[str, Any]:
    if unavailable_reason:
        status = "unknown"
    elif not positive_targets:
        status = "unknown"
        unavailable_reason = "no_positive_coverage_targets"
    else:
        found = [target for target in positive_targets if target in actual_ids]
        status = "pass" if len(found) == len(positive_targets) else "partial" if found else "fail"
    losses = (
        [value for value in positive_targets if value in previous_ids and value not in actual_ids]
        if previous_ids is not None
        else []
    )
    return {
        "stage": stage,
        "status": status,
        "actual_external_ids": actual_ids,
        "positive_targets": positive_targets,
        "positive_found": [value for value in positive_targets if value in actual_ids],
        "positive_missing": [value for value in positive_targets if value not in actual_ids],
        "lost_from_previous_stage": losses,
        "unverified_reason": unavailable_reason,
    }


def _check_dispositions(
    actual: Mapping[str, Any],
    expected: Mapping[str, Any],
    technical_error: Any,
    *,
    only_if_evaluated: bool = False,
) -> dict[str, Any]:
    if technical_error:
        return {"status": "unknown", "checks": {}}
    if not expected:
        return {"status": "unmeasured", "checks": {}}
    checks = {
        external_id: {
            "expected": outcome,
            "actual": actual.get(external_id),
            "status": ("not_evaluated" if only_if_evaluated else "unknown")
            if external_id not in actual
            else "pass"
            if actual[external_id] == outcome
            else "fail",
        }
        for external_id, outcome in expected.items()
    }
    statuses = {check["status"] for check in checks.values()}
    status = (
        "fail"
        if "fail" in statuses
        else "unknown"
        if "unknown" in statuses
        else "not_evaluated"
        if "not_evaluated" in statuses
        else "pass"
    )
    return {"status": status, "checks": checks}


def _check_structured_expectations(
    graph: Mapping[str, Any], expected: Mapping[str, Any], technical_error: Any
) -> dict[str, Any]:
    if technical_error:
        return {"status": "unknown", "checks": {}}
    actual_pairs: dict[str, Mapping[str, Any]] = {}
    actual_conditions: dict[tuple[str | None, str], str] = {}
    evaluations = graph.get("candidate_evaluations", [])
    for candidate in evaluations if isinstance(evaluations, list) else []:
        if not isinstance(candidate, Mapping):
            continue
        reasons = candidate.get("reasons", [])
        for reason in reasons if isinstance(reasons, list) else []:
            if not isinstance(reason, Mapping) or reason.get("criterion") != "compatibility":
                continue
            pair_key = reason.get("pair_key")
            if isinstance(pair_key, str):
                actual_pairs[pair_key] = reason
            condition_checks = reason.get("condition_checks", [])
            for check in condition_checks if isinstance(condition_checks, list) else []:
                if isinstance(check, Mapping) and isinstance(check.get("condition_id"), str):
                    actual_conditions[
                        (pair_key if isinstance(pair_key, str) else None, check["condition_id"])
                    ] = str(check.get("status", "unknown"))

    def collect_pair_sources(value: Any) -> None:
        if isinstance(value, Mapping):
            data = value.get("data", value)
            if isinstance(data, Mapping):
                key, verdict = data.get("pair_key"), data.get("verdict")
                if isinstance(key, str) and verdict is not None:
                    actual_pairs[key] = {"verdict": verdict}
            for nested in value.values():
                if isinstance(nested, (Mapping, list)):
                    collect_pair_sources(nested)
        elif isinstance(value, list):
            for nested in value:
                collect_pair_sources(nested)

    result = graph.get("result", {})
    reference = graph.get("reference_result", {})
    reference_component = graph.get("reference_component", {})
    for source_root in (
        result.get("sources", {}) if isinstance(result, Mapping) else {},
        reference.get("sources", {}) if isinstance(reference, Mapping) else {},
        reference_component.get("sources", {}) if isinstance(reference_component, Mapping) else {},
    ):
        collect_pair_sources(source_root)

    checks: dict[str, dict[str, Any]] = {}
    expected_pair = expected.get("pair")
    if isinstance(expected_pair, Mapping):
        key = expected_pair.get("key")
        if isinstance(key, str) and expected_pair.get("verdict") is not None:
            actual = actual_pairs.get(key)
            actual_verdict = actual.get("verdict") if actual else None
            checks[f"pair:{key}:verdict"] = {
                "expected": expected_pair["verdict"],
                "actual": actual_verdict,
                "status": "unknown"
                if actual_verdict is None
                else "pass"
                if actual_verdict == expected_pair["verdict"]
                else "fail",
            }
    expected_conditions = expected.get("condition_checks")
    if isinstance(expected_conditions, Mapping):
        condition_pair_key = expected_conditions.get("pair_key")
        for condition_id, wanted in expected_conditions.items():
            if condition_id == "pair_key":
                continue
            actual_condition = actual_conditions.get(
                (str(condition_pair_key) if condition_pair_key else None, str(condition_id))
            )
            checks[f"condition:{condition_pair_key}:{condition_id}"] = {
                "expected": wanted,
                "actual": actual_condition,
                "status": "unknown"
                if actual_condition is None
                else "pass"
                if actual_condition == wanted
                else "fail",
            }
    if not checks:
        return {"status": "unmeasured", "checks": {}}
    statuses = {check["status"] for check in checks.values()}
    status = "fail" if "fail" in statuses else "unknown" if "unknown" in statuses else "pass"
    return {"status": status, "checks": checks}


def _named_lexical_ids(
    messages: list[Any],
) -> tuple[list[str], dict[str, str], dict[str, dict[str, Any]]]:
    actual_ids: list[str] = []
    internal_to_external: dict[str, str] = {}
    ranks: dict[str, dict[str, Any]] = {}
    for message in messages:
        if not isinstance(message, Mapping) or message.get("name") != "search_stones_lexical":
            continue
        content = message.get("content")
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except (ValueError, TypeError):
                continue
        if not isinstance(content, list):
            continue
        for rank, card in enumerate(content, start=1):
            if not isinstance(card, Mapping):
                continue
            internal_id = card.get("id")
            external_id = card.get("stone_external_id", card.get("external_id"))
            if isinstance(internal_id, str) and isinstance(external_id, str):
                internal_to_external[internal_id] = external_id
                actual_ids.append(external_id)
                ranks[external_id] = {
                    "lexical_rank": rank,
                    "semantic_rank": None,
                    "rrf_score": None,
                    "retrieval_rank": None,
                    "in_pool": None,
                }
    return _unique(actual_ids), internal_to_external, ranks


def _stage_statuses(
    applicability: str,
    positive: list[str],
    stage_ids: Mapping[str, list[str]],
    stage_presence: Mapping[str, bool],
    technical_error: str | None,
    named_lookup: bool,
    reason: Any,
) -> list[dict[str, Any]]:
    previous_for = {
        "lexical": None,
        "semantic": None,
        "engine_union": None,
        "rrf": "engine_union",
        "shortlist": "rrf",
        "evidence": "shortlist",
        "decision": "evidence",
        "answer": "decision",
    }
    reports = []
    for stage in STAGES:
        predecessor = previous_for[stage]
        previous_ids = stage_ids[predecessor] if predecessor is not None else None
        not_applicable_reason = None
        if named_lookup and stage in {"semantic", "engine_union", "rrf"}:
            not_applicable_reason = "exact_name_lexical_route"
        elif applicability == "not_applicable":
            not_applicable_reason = str(reason or "reference_only_request")
        elif applicability == "recommendation_filter_only":
            not_applicable_reason = "filter_ineligible_target_only"

        if not_applicable_reason is not None:
            report = _target_stage(stage, stage_ids[stage], [], previous_ids)
            report.update(status="not_applicable", unverified_reason=not_applicable_reason)
        elif applicability == "unsupported_capability":
            report = _target_stage(
                stage,
                stage_ids[stage],
                positive,
                previous_ids,
                unavailable_reason="unsupported_multi_name_comparison",
            )
            report["status"] = "capability_unverified"
        else:
            missing = None if stage_presence[stage] else f"missing_{stage}_output"
            report = _target_stage(
                stage,
                stage_ids[stage],
                positive,
                previous_ids,
                unavailable_reason=technical_error or missing,
            )
        reports.append(report)
    return reports


def evaluate_scenario_record(
    record: Mapping[str, Any], scenario_targets: Mapping[str, Any]
) -> dict[str, Any]:
    """Compare captured outputs to explicit targets, retaining unknown as unknown."""
    applicability = str(scenario_targets["stage_applicability"])
    positive = list(scenario_targets.get("positive_retrieval_external_ids", []))
    counterexamples = list(scenario_targets.get("counterexample_external_ids", []))
    filter_ineligible = list(scenario_targets.get("filter_ineligible_external_ids", []))
    graph = record.get("graph_state")
    technical_error = record.get("technical_error") or (
        "missing_graph_state" if not isinstance(graph, Mapping) else None
    )
    if not isinstance(graph, Mapping):
        graph = {}

    messages = graph.get("messages", [])
    messages = messages if isinstance(messages, list) else []
    named_lookup = bool(
        isinstance(graph.get("reference_request"), Mapping)
        and graph["reference_request"].get("recommendation_name")
    )
    cards = graph.get("candidate_cards", {})
    internal_to_external = (
        {
            internal_id: str(card["external_id"])
            for internal_id, card in cards.items()
            if isinstance(cards, Mapping)
            and isinstance(internal_id, str)
            and isinstance(card, Mapping)
            and isinstance(card.get("external_id"), str)
        }
        if isinstance(cards, Mapping)
        else {}
    )
    evaluations = graph.get("candidate_evaluations", [])
    for candidate in evaluations if isinstance(evaluations, list) else []:
        if isinstance(candidate, Mapping):
            internal_id, external_id = candidate.get("stone_id"), candidate.get("external_id")
            if isinstance(internal_id, str) and isinstance(external_id, str):
                internal_to_external.setdefault(internal_id, external_id)

    provenance = graph.get("retrieval_provenance", [])
    provenance = provenance if isinstance(provenance, list) else []
    lexical_ranked: list[tuple[int, str]] = []
    semantic_ranked: list[tuple[int, str]] = []
    rrf_ranked: list[tuple[int, str]] = []
    ranks: dict[str, dict[str, Any]] = {}
    for hit in provenance:
        if not isinstance(hit, Mapping) or not isinstance(hit.get("external_id"), str):
            continue
        external_id = hit["external_id"]
        internal_id = hit.get("stone_id")
        if isinstance(internal_id, str):
            internal_to_external.setdefault(internal_id, external_id)
        lexical_rank = hit.get("lexical_rank")
        semantic_rank = hit.get("semantic_rank")
        retrieval_rank = hit.get("retrieval_rank")
        if isinstance(lexical_rank, int):
            lexical_ranked.append((lexical_rank, external_id))
        if isinstance(semantic_rank, int):
            semantic_ranked.append((semantic_rank, external_id))
        if isinstance(retrieval_rank, int) and hit.get("in_pool") is True:
            rrf_ranked.append((retrieval_rank, external_id))
        ranks[external_id] = {
            "lexical_rank": lexical_rank,
            "semantic_rank": semantic_rank,
            "rrf_score": hit.get("rrf_score"),
            "retrieval_rank": retrieval_rank,
            "in_pool": hit.get("in_pool"),
        }

    lexical = [external_id for _, external_id in sorted(lexical_ranked)]
    semantic = [external_id for _, external_id in sorted(semantic_ranked)]
    if named_lookup:
        lexical, named_map, named_ranks = _named_lexical_ids(messages)
        internal_to_external.update(named_map)
        ranks.update(named_ranks)
    engine_union = _unique([*lexical, *semantic])
    rrf = [external_id for _, external_id in sorted(rrf_ranked)]
    selected = graph.get("selected_stone_ids", [])
    selected = selected if isinstance(selected, list) else []
    shortlist = _to_external(selected, internal_to_external)

    evaluation_sources = graph.get("evaluation_sources", {})
    source_ids = set(evaluation_sources) if isinstance(evaluation_sources, Mapping) else set()
    source_ids.update(
        f"stone-card:{internal_id}"
        for internal_id in cards
        if isinstance(cards, Mapping) and isinstance(internal_id, str)
    )
    evidence_ids: list[str] = []
    evidence_detail: dict[str, list[dict[str, Any]]] = {}
    for candidate in evaluations if isinstance(evaluations, list) else []:
        if not isinstance(candidate, Mapping) or not isinstance(candidate.get("reasons"), list):
            continue
        external_id = candidate.get("external_id")
        if not isinstance(external_id, str):
            continue
        refs: list[dict[str, Any]] = []
        for reason in candidate["reasons"]:
            if not isinstance(reason, Mapping):
                continue
            source_id = reason.get("source_id")
            if isinstance(source_id, str) and source_id in source_ids:
                refs.append(
                    {
                        "source_id": source_id,
                        "criterion": reason.get("criterion"),
                        "quote": None,
                        "source_present": True,
                        "binding": "reason_source_id",
                    }
                )
            evidence_items = reason.get("evidence", [])
            for evidence in evidence_items if isinstance(evidence_items, list) else []:
                if not isinstance(evidence, Mapping):
                    continue
                evidence_source = evidence.get("source_id")
                if not isinstance(evidence_source, str):
                    continue
                refs.append(
                    {
                        "source_id": evidence_source,
                        "criterion": reason.get("criterion"),
                        "quote": evidence.get("quote"),
                        "source_present": evidence_source in source_ids,
                        "binding": "reason_evidence",
                    }
                )
        valid_refs = [ref for ref in refs if ref["source_present"]]
        if valid_refs:
            evidence_ids.append(external_id)
        if refs:
            evidence_detail[external_id] = refs

    decision = _to_external(
        [
            candidate.get("stone_id")
            for candidate in evaluations
            if isinstance(candidate, Mapping) and isinstance(candidate.get("stone_id"), str)
        ]
        if isinstance(evaluations, list)
        else [],
        internal_to_external,
    )
    result = graph.get("result", {})
    answer_decisions = result.get("candidate_decisions", []) if isinstance(result, Mapping) else []
    answer_internal_ids = (
        [
            candidate.get("stone_id")
            for candidate in answer_decisions
            if isinstance(candidate, Mapping) and isinstance(candidate.get("stone_id"), str)
        ]
        if isinstance(answer_decisions, list)
        else []
    )
    answer = _to_external(answer_internal_ids, internal_to_external)
    decision_internal_ids = (
        [
            candidate.get("stone_id")
            for candidate in evaluations
            if isinstance(candidate, Mapping) and isinstance(candidate.get("stone_id"), str)
        ]
        if isinstance(evaluations, list)
        else []
    )
    recommended = graph.get("recommended_stone_ids", [])
    recommended_external_ids = _to_external(
        recommended if isinstance(recommended, list) else [], internal_to_external
    )
    stage_ids = {
        "lexical": _unique(lexical),
        "semantic": _unique(semantic),
        "engine_union": engine_union,
        "rrf": _unique(rrf),
        "shortlist": shortlist,
        "evidence": _unique(evidence_ids),
        "decision": decision,
        "answer": answer,
    }
    stage_presence = {
        "lexical": "retrieval_provenance" in graph or named_lookup,
        "semantic": "retrieval_provenance" in graph,
        "engine_union": "retrieval_provenance" in graph,
        "rrf": "retrieval_provenance" in graph,
        "shortlist": "selected_stone_ids" in graph,
        "evidence": "candidate_evaluations" in graph,
        "decision": "candidate_evaluations" in graph,
        "answer": isinstance(result, Mapping) and "candidate_decisions" in result,
    }
    stage_reports = _stage_statuses(
        applicability,
        positive,
        stage_ids,
        stage_presence,
        str(technical_error) if technical_error else None,
        named_lookup,
        scenario_targets.get("reason"),
    )
    unmapped_by_stage = {
        "shortlist": _unmapped_ids(selected, internal_to_external),
        "decision": _unmapped_ids(decision_internal_ids, internal_to_external),
        "answer": _unmapped_ids(answer_internal_ids, internal_to_external),
    }
    for stage_report in stage_reports:
        unmapped = unmapped_by_stage.get(stage_report["stage"], [])
        stage_report["unmapped_internal_ids"] = unmapped
        if unmapped and stage_report["status"] not in {"not_applicable", "capability_unverified"}:
            stage_report["status"] = "unknown"
            stage_report["unverified_reason"] = "unmapped_internal_ids"

    recommendation_outcomes = (
        {
            candidate["external_id"]: candidate.get("outcome")
            for candidate in evaluations
            if isinstance(candidate, Mapping) and isinstance(candidate.get("external_id"), str)
        }
        if isinstance(evaluations, list)
        else {}
    )
    expected_dispositions = scenario_targets.get("expected_dispositions", {})
    counterexample_recommended = [
        value for value in counterexamples if value in recommended_external_ids
    ]
    counterexample_not_evaluated = [value for value in counterexamples if value not in decision]
    counterexample_status = (
        "unknown"
        if technical_error or "recommended_stone_ids" not in graph
        else "fail"
        if counterexample_recommended
        else "not_evaluated"
        if counterexample_not_evaluated
        else "pass"
        if counterexamples
        else "not_applicable"
    )
    plan_status = graph.get("plan_status")
    criteria_status = graph.get("criteria_status")
    selection_status = graph.get("selection_status")
    question_coverage_status = graph.get("question_coverage_status")
    parsed_question = graph.get("parsed_question", {})
    permitted = graph.get("permitted_tools", [])
    blocked = graph.get("blocked_tools", [])
    recommendation_requested = bool(
        isinstance(parsed_question, Mapping)
        and parsed_question.get("recommendation_limit", 0)
    ) or (
        isinstance(permitted, list) and "search_candidates" in permitted
    ) or (isinstance(blocked, list) and "search_candidates" in blocked)
    answer_recommendation_status = (
        result.get("recommendation_status") if isinstance(result, Mapping) else None
    )
    if not recommendation_requested:
        recommendation_gate = {"status": "not_applicable", "coverage_status": question_coverage_status}
    elif technical_error:
        recommendation_gate = {"status": "unknown", "coverage_status": question_coverage_status}
    elif question_coverage_status == "complete" and answer_recommendation_status != "blocked_question_coverage":
        recommendation_gate = {"status": "pass", "coverage_status": question_coverage_status}
    elif question_coverage_status in {"incomplete", "uncertain"} and answer_recommendation_status == "blocked_question_coverage":
        recommendation_gate = {
            "status": "blocked_incomplete_coverage",
            "coverage_status": question_coverage_status,
        }
    elif question_coverage_status in {"incomplete", "uncertain"}:
        recommendation_gate = {"status": "fail", "coverage_status": question_coverage_status}
    else:
        recommendation_gate = {
            "status": "unknown",
            "coverage_status": question_coverage_status,
        }
    bad_assessment_statuses = {
        "invalid_response",
        "invalid_source_ref",
        "invalid_binding",
        "assessment_error",
    }
    known_failures = bool(
        (plan_status is not None and plan_status != "accepted")
        or (criteria_status is not None and criteria_status != "parsed")
        or graph.get("stop_reason")
        or selection_status == "invalid_selection"
        or graph.get("assessment_status") in bad_assessment_statuses
        or graph.get("reference_assessment_status") in bad_assessment_statuses
        or not isinstance(result, Mapping)
        or (isinstance(result, Mapping) and not isinstance(result.get("answer"), str))
    )
    required_state_missing = (
        plan_status is None or criteria_status is None or not isinstance(result, Mapping)
    )
    workflow_integrity = (
        "unknown"
        if technical_error or (required_state_missing and not known_failures)
        else "fail"
        if known_failures
        else "pass"
    )
    return {
        "case_id": record.get("case_id"),
        "stage_applicability": applicability,
        "technical_error": technical_error,
        "workflow_integrity": {
            "status": workflow_integrity,
            "plan_status": plan_status,
            "criteria_status": criteria_status,
            "selection_status": selection_status,
            "reference_assessment_status": graph.get("reference_assessment_status"),
            "candidate_assessment_status": graph.get("assessment_status"),
            "question_coverage_status": question_coverage_status,
            "answer_present": bool(result.get("answer")) if isinstance(result, Mapping) else False,
            "note": "Execution integrity only; this is not a semantic answer-quality score.",
        },
        "stages": stage_reports,
        "engine_ranks": ranks,
        "evidence_detail": evidence_detail,
        "structured_expectations": _check_structured_expectations(
            graph,
            record.get("expected", {}) if isinstance(record.get("expected"), Mapping) else {},
            technical_error,
        ),
        "recommendations": {
            "external_ids": recommended_external_ids,
            "candidate_outcomes": recommendation_outcomes,
            "expected_dispositions": expected_dispositions,
            "disposition_check": _check_dispositions(
                recommendation_outcomes,
                expected_dispositions,
                technical_error,
                only_if_evaluated=bool(
                    scenario_targets.get("expected_dispositions_when_evaluated")
                ),
            ),
            "coverage_gate": recommendation_gate,
        },
        "counterexamples": {
            "external_ids": counterexamples,
            "retrieved": [
                value
                for value in counterexamples
                if value in set(lexical) | set(semantic) | set(rrf)
            ],
            "shortlisted": [value for value in counterexamples if value in shortlist],
            "recommended": counterexample_recommended,
            "status": counterexample_status,
            "not_evaluated": counterexample_not_evaluated,
            "does_not_establish_positive_coverage": True,
        },
        "filter_ineligible_targets": {
            "external_ids": filter_ineligible,
            "retrieved": [
                value
                for value in filter_ineligible
                if value in set(lexical) | set(semantic) | set(rrf)
            ],
            "status": "reported_separately_from_recall",
        },
        "semantic_answer_assessment": {
            "status": "unmeasured",
            "reason": "semantic_judge_disabled_or_not_supplied",
        },
        "semantic_judge_input": {
            "final_answer": result.get("answer") if isinstance(result, Mapping) else None,
            "actual_supplied_sources": result.get("sources", {})
            if isinstance(result, Mapping)
            else {},
            "required_assertions": record.get("expected", {}).get("required", [])
            if isinstance(record.get("expected"), Mapping)
            else [],
            "forbidden_assertions": record.get("expected", {}).get("forbidden", [])
            if isinstance(record.get("expected"), Mapping)
            else [],
            "uses_oracle_fixture_sources": False,
        },
        "actual_result": record.get("response"),
    }


def evaluate_run(run: Mapping[str, Any], targets: Mapping[str, Any]) -> dict[str, Any]:
    target_by_id = targets["scenarios"]
    source_records = [record for record in run.get("records", []) if isinstance(record, Mapping)]
    records_by_id: dict[str, Mapping[str, Any]] = {}
    duplicate_ids: set[str] = set()
    for record in source_records:
        case_id = record.get("case_id")
        if not isinstance(case_id, str):
            continue
        if case_id in records_by_id:
            duplicate_ids.add(case_id)
        records_by_id[case_id] = record
    selected_ids = run.get("selected_case_ids")
    case_ids = selected_ids if isinstance(selected_ids, list) else list(records_by_id)
    reports = []
    missing_target_ids = []
    for case_id in case_ids:
        if not isinstance(case_id, str):
            continue
        if case_id not in target_by_id:
            missing_target_ids.append(case_id)
            reports.append(
                {
                    "case_id": case_id,
                    "technical_error": "missing_target_configuration",
                    "workflow_integrity": {"status": "unknown"},
                    "semantic_answer_assessment": {"status": "unmeasured"},
                }
            )
            continue
        captured_record = records_by_id.get(case_id)
        if captured_record is None:
            report_record: Mapping[str, Any] = {
                "case_id": case_id,
                "technical_error": "missing_case_record",
            }
        elif case_id in duplicate_ids:
            report_record = {**captured_record, "technical_error": "duplicate_case_records"}
        else:
            report_record = captured_record
        reports.append(evaluate_scenario_record(report_record, target_by_id[case_id]))
    unexpected_record_ids = sorted(set(records_by_id) - set(target_by_id))
    return {
        "suite_id": run.get("suite_id"),
        "source_run_status": run.get("status"),
        "semantic_judge": "unmeasured",
        "archive_integrity": {
            "duplicate_case_record_ids": sorted(duplicate_ids),
            "selected_cases_missing_target_config": missing_target_ids,
            "unexpected_record_case_ids": unexpected_record_ids,
        },
        "scenario_reports": reports,
    }
