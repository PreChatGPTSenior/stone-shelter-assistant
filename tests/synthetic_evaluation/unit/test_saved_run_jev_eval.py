"""Offline validation of the Jev adapter and saved-result preparation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from deepeval.metrics import JevEval
from deepeval.test_case import LLMTestCase, SingleTurnParams
from pytest import approx

from tests.evaluation.support.jev_saved_run import (
    JEv_LABELS,
    OpenRouterJevModel,
    _usage_and_answers,
    criterion_gates_pass,
    criterion_questions,
    sanitize_payload,
    score_meets_threshold,
)
from tests.evaluation.test_saved_run_jev_eval import (
    _load_saved_case,
    _model_slug,
    _select_sources,
    _validate_batch_identity,
    _workflow_context,
)


def _response(request: dict[str, Any]) -> dict[str, Any]:
    answers = {}
    for key, question in request["questions"].items():
        labels = tuple(question.get("criteria", JEv_LABELS))
        if labels == JEv_LABELS:
            choice = "satisfies"
            probabilities = {
                "satisfies": 0.9,
                "partially_satisfies": 0.06,
                "does_not_satisfy": 0.04,
            }
        else:
            choice = "substantive" if "substantive" in labels else "satisfies"
            remaining = 0.1 / (len(labels) - 1)
            probabilities = {label: 0.9 if label == choice else remaining for label in labels}
        answers[key] = {
            "type": "choice",
            "choice": choice,
            "confidence": 0.9,
            "probabilities": probabilities,
        }
    return {
        "model": "typesafe/jev-1.14-20261014",
        "answers": answers,
        "usage": {"input_tokens": 123, "output_tokens": 35, "cost": 0.00002},
    }


class _HttpResponse:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self) -> _HttpResponse:
        return self

    def __exit__(self, *args: Any) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def test_saved_result_preflight_loads_one_matching_answer_and_observation_archive() -> None:
    source = (
        Path(__file__).resolve().parents[3]
        / "test-evaluation-results/Q01/STPY-langview-20261115-r02/result.json"
    )
    source_bytes, result, observation_bytes, observations = _load_saved_case(source)
    assert source_bytes
    assert observation_bytes
    assert result["case_id"] == "Q01"
    assert isinstance(observations["observations"], list)
    context, missing = _workflow_context(result)
    assert context.get("candidate_decisions") == result["graph_state"]["result"].get(
        "candidate_decisions"
    )
    assert "assessment" in missing
    assert "assessment_status" in missing
    assert result["graph_state"]["result"]["sources"]


def test_session_selection_requires_the_complete_twenty_archive_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SAVED_JEV_RESULT_PATH", raising=False)
    monkeypatch.setenv("SAVED_JEV_SESSION_ID", "STPY-langview-20261115-r02")
    sources = _select_sources()
    assert len(sources) == 20
    assert [path.parent.parent.name for path in sources] == [f"Q{i:02d}" for i in range(1, 21)]
    assert all(path.name == "result.json" for path in sources)
    for path in sources:
        _, result, _, _ = _load_saved_case(path)
        _validate_batch_identity(path, result, "STPY-langview-20261115-r02")
        questions, criteria, _ = criterion_questions(result["case_id"], result["expected"])
        assert len(questions) == len(criteria)
        for question, criterion in zip(questions, criteria, strict=True):
            if criterion.get("gate"):
                assert set(question.options) == {
                    "substantive",
                    "partial_but_useful",
                    "clarification_or_error_only",
                }
            else:
                assert {"satisfies", "partially_satisfies", "does_not_satisfy"} <= set(
                    question.options
                )


def test_session_selection_rejects_ambiguous_or_unsafe_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SAVED_JEV_RESULT_PATH", "/tmp/result.json")
    monkeypatch.setenv("SAVED_JEV_SESSION_ID", "STPY-langview-20261115-r02")
    with pytest.raises(ValueError, match="exactly one"):
        _select_sources()
    monkeypatch.delenv("SAVED_JEV_RESULT_PATH")
    monkeypatch.setenv("SAVED_JEV_SESSION_ID", "../private")
    with pytest.raises(ValueError, match="only letters"):
        _select_sources()


def test_criteria_preserve_each_reviewed_required_and_forbidden_item() -> None:
    questions, criteria, unmeasured = criterion_questions(
        "Q01", {"required": ["Report availability."], "forbidden": ["Do not infer history."]}
    )
    assert len(questions) == 2
    assert criteria == [
        {
            "id": "required-1",
            "direction": "required",
            "source_text": "Report availability.",
            "text": "Report availability.",
        },
        {
            "id": "forbidden-1",
            "direction": "forbidden",
            "source_text": "Do not infer history.",
            "text": "Do not infer history.",
        },
    ]
    assert not unmeasured
    assert "final answer text only" in questions[0].question
    assert "Report availability." in questions[0].question
    assert "comply with this prohibition" in questions[1].question
    assert "Do not infer history." in questions[1].question


def test_conditional_and_prohibition_criteria_distinguish_omission_from_violation() -> None:
    q02_questions, q02_criteria, _ = criterion_questions(
        "Q02",
        {
            "required": [
                "Sir Pebble has biography support but the granite pair conditions are unconfirmed.",
                "Homeward Pumice has no individual quiet-home evidence; Professor's generic biography does not establish it.",
                "Svetlana's individual biography describes loud early-morning singing; it does not support a quiet-home requirement. If she is evaluated, preserve that conflict.",
            ],
            "forbidden": [],
        },
    )
    assert len(q02_questions) == 3
    assert "not_applicable" not in q02_questions[0].options
    assert q02_criteria[0]["direction"] == "required"
    assert "An omitted required positive statement does not satisfy" in q02_questions[0].question
    for question in q02_questions[1:]:
        assert question.options["not_applicable"] is None
        assert "Select not_applicable" in question.question

    q08_questions, q08_criteria, _ = criterion_questions(
        "Q08",
        {
            "required": [
                "Both granite condition checks have no applicable positive facts and remain unknown.",
                "Typed agreements, if extracted, retain BASALT+GNEISS scope.",
            ],
            "forbidden": ["Do not widen scoped facts to household-wide facts."],
        },
    )
    assert "not_applicable" not in q08_questions[0].options
    assert "not_applicable" in q08_questions[1].options
    assert "guide's prescribed agreement is not evidence" in q08_questions[0].question
    assert "Quoting a source rule with its pair scope is not widening" in q08_questions[2].question
    assert "silence complies" in q08_questions[2].question
    assert q08_criteria[0]["direction"] == "required"

    q09_questions, _, _ = criterion_questions(
        "Q09",
        {
            "required": [
                "Madame's trigger_notes contradict the vacuum requirement.",
                "If evaluated, exclude her for the unmet requirement even though she enjoys human company.",
            ],
            "forbidden": ["Positive socialization must not cancel the mandatory trigger conflict."],
        },
    )
    assert "An omitted required positive statement does not satisfy" in q09_questions[0].question
    assert "not_applicable" in q09_questions[1].options
    assert (
        "If it does not make that claim, the prohibition is satisfied" in q09_questions[2].question
    )
    assert "not_applicable" not in q09_questions[2].options

    q16_questions, _, _ = criterion_questions(
        "Q16",
        {
            "required": [
                "Homeward Pumice is AVAILABLE and ENJOYS_OTHER_STONES is profile evidence for general sociability.",
                "Individual granite-specific compatibility findings remain empty unless explicit source evidence exists.",
            ],
            "forbidden": [],
        },
    )
    assert "not_applicable" not in q16_questions[0].options
    assert "not_applicable" in q16_questions[1].options
    assert "Select not_applicable when it makes no such claim" in q16_questions[1].question

    q17_questions, _, _ = criterion_questions(
        "Q17",
        {
            "required": [
                "If Professor is evaluated, the required character evidence remains unknown."
            ],
            "forbidden": ["No biography quote may migrate between these stones."],
        },
    )
    assert "not_applicable" in q17_questions[0].options
    assert "If it does not do so, the prohibition is satisfied" in q17_questions[1].question
    assert "not_applicable" not in q17_questions[1].options

    q11_questions, _, _ = criterion_questions(
        "Q11",
        {
            "required": [
                "Velvet Slate cannot be recommended because current status is RETURNED.",
                "If assessed, trigger_notes contradict the loud-music requirement.",
            ],
            "forbidden": [
                "Caregiver experience does not change adoption status or erase a trigger."
            ],
        },
    )
    assert "not_applicable" in q11_questions[1].options
    assert "If it makes no such claim, the prohibition is satisfied" in q11_questions[2].question

    for case_id, criterion, positive_prompt in (
        (
            "Q07",
            "Do not silently drop the denial or describe both conditions as fulfilled.",
            "Omitting the denial is a failure",
        ),
        (
            "Q18",
            "Do not accept a partial single-name answer as a passing comparison.",
            "A single-name or empty answer does not satisfy",
        ),
        (
            "Q20",
            "Keep geological care facts separate from fictional temperament.",
            "Omitting the required distinction",
        ),
    ):
        questions, _, _ = criterion_questions(case_id, {"required": [], "forbidden": [criterion]})
        assert positive_prompt in questions[0].question


def test_q06_substantive_answer_gate_cannot_be_compensated_by_high_average() -> None:
    questions, criteria, _ = criterion_questions(
        "Q06", {"required": ["Useful recommendation."], "forbidden": []}
    )
    assert len(questions) == 2
    outcomes = [
        {"applicable": True, "probabilities": {"satisfies": 1.0}},
        {
            "applicable": True,
            "probabilities": {
                "substantive": 0.0,
                "partial_but_useful": 0.0,
                "clarification_or_error_only": 1.0,
            },
        },
    ]
    gates_passed, gate_results = criterion_gates_pass(criteria, outcomes)
    assert not gates_passed
    assert gate_results == [
        {"id": "answer-substance-gate", "selected": "clarification_or_error_only", "passed": False}
    ]
    outcomes[-1]["probabilities"] = {
        "substantive": 0.9,
        "partial_but_useful": 0.1,
        "clarification_or_error_only": 0.0,
    }
    gates_passed, _ = criterion_gates_pass(criteria, outcomes)
    assert gates_passed


def test_score_threshold_tolerance_is_small_and_does_not_override_gates() -> None:
    assert score_meets_threshold(0.7999999999999999, 0.8)
    assert not score_meets_threshold(0.799999, 0.8)
    criteria = [{"id": "gate", "gate": True}]
    outcomes = [{"probabilities": {"clarification_or_error_only": 1.0}}]
    gates_passed, _ = criterion_gates_pass(criteria, outcomes)
    assert score_meets_threshold(0.7999999999999999, 0.8) and not gates_passed


@pytest.mark.asyncio
async def test_q14_history_choice_excludes_absent_history_but_penalizes_wrong_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requested_history_choice = "not_applicable"

    def fake_urlopen(request: Any, timeout: int) -> _HttpResponse:
        assert timeout == 120
        payload = json.loads(request.data)
        response = _response(payload)
        history = response["answers"]["q_1"]
        history["choice"] = requested_history_choice
        history["probabilities"] = {
            "satisfies": 0.05,
            "partially_satisfies": 0.0 if requested_history_choice == "not_applicable" else 0.05,
            "does_not_satisfy": 0.05 if requested_history_choice == "not_applicable" else 0.9,
            "not_applicable": 0.9 if requested_history_choice == "not_applicable" else 0.0,
        }
        return _HttpResponse(json.dumps(response).encode())

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    model = OpenRouterJevModel("typesafe/jev-1.14-20261014", "fake-jev-key")
    questions, criteria, _ = criterion_questions(
        "Q14",
        {
            "required": [
                "Report AVAILABLE from PostgreSQL.",
                "If discussing history, reservation ended after reservation began.",
            ],
            "forbidden": ["Do not report RESERVED based on a search hit from the older event."],
        },
    )
    assert criteria[1]["applicability_option"] == "not_applicable"

    async def measure() -> float:
        metric = JevEval(
            name="offline_q14_history_applicability",
            evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT],
            questions=questions,
            system_one_model=model,
        )
        return await metric.a_measure(
            LLMTestCase(input="status?", actual_output="AVAILABLE"), _show_indicator=False
        )

    absent_history_score = await measure()
    assert absent_history_score == approx(0.93)
    requested_history_choice = "does_not_satisfy"
    contradictory_history_score = await measure()
    assert contradictory_history_score < absent_history_score


@pytest.mark.asyncio
async def test_q06_gate_labels_reach_jev_and_override_a_high_average(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate_choice = "clarification_or_error_only"
    sent: list[dict[str, Any]] = []

    def fake_urlopen(request: Any, timeout: int) -> _HttpResponse:
        assert timeout == 120
        payload = json.loads(request.data)
        sent.append(payload)
        response = _response(payload)
        gate_key = next(
            key
            for key, question in payload["questions"].items()
            if "clarification_or_error_only" in question["criteria"]
        )
        gate = response["answers"][gate_key]
        gate["choice"] = gate_choice
        gate["probabilities"] = {
            "substantive": 0.9 if gate_choice == "substantive" else 0.0,
            "partial_but_useful": 0.1 if gate_choice == "substantive" else 0.0,
            "clarification_or_error_only": 0.0 if gate_choice == "substantive" else 1.0,
        }
        return _HttpResponse(json.dumps(response).encode())

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    model = OpenRouterJevModel("typesafe/jev-1.14-20261014", "fake-jev-key")
    expected = {"required": [f"Useful item {index}." for index in range(8)], "forbidden": []}
    questions, criteria, _ = criterion_questions("Q06", expected)

    async def measure() -> tuple[float, bool, list[dict[str, Any]]]:
        metric = JevEval(
            name="offline_q06_substantive_gate",
            evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT],
            questions=questions,
            system_one_model=model,
            threshold=0.8,
        )
        await metric.a_measure(
            LLMTestCase(input="recommend a granite stone", actual_output="Clarify."),
            _show_indicator=False,
        )
        assert metric.score_breakdown is not None
        assert metric.score is not None
        gates_passed, gates = criterion_gates_pass(criteria, metric.score_breakdown)
        return metric.score, gates_passed, gates

    clarification_score, clarification_gate, _ = await measure()
    assert clarification_score > 0.8
    assert not clarification_gate
    gate_question = next(
        question
        for question in sent[0]["questions"].values()
        if "clarification_or_error_only" in question["criteria"]
    )
    assert set(gate_question["criteria"]) == {
        "substantive",
        "partial_but_useful",
        "clarification_or_error_only",
    }

    gate_choice = "substantive"
    substantive_score, substantive_gate, _ = await measure()
    assert substantive_score > 0.8
    assert substantive_gate


def test_saved_case_criteria_preflight_marks_procedure_out_of_scope() -> None:
    _, result, _, _ = _load_saved_case(
        Path(__file__).resolve().parents[3]
        / "test-evaluation-results/Q09/STPY-langview-20261115-r02/result.json"
    )
    questions, criteria, unmeasured = criterion_questions(result["case_id"], result["expected"])
    assert questions
    assert criteria
    assert [item["status"] for item in unmeasured] == ["not_measured"]
    assert "retrieval" in unmeasured[0]["reason"]


def test_jev_choice_payload_rejects_missing_or_inconsistent_answers() -> None:
    request: dict[str, Any] = {"questions": {"q_0": {}, "q_1": {}}}
    parsed = _usage_and_answers(
        _response(request), {key: set(JEv_LABELS) for key in request["questions"]}
    )
    assert set(parsed[0]["choices"]) == {"q_0", "q_1"}
    with pytest.raises(ValueError, match="answer keys"):
        _usage_and_answers(
            _response({"questions": {"q_0": {}}}),
            {"q_0": set(JEv_LABELS), "q_1": set(JEv_LABELS)},
        )
    bad = _response(request)
    bad["answers"]["q_0"]["choice"] = "does_not_satisfy"
    with pytest.raises(ValueError, match="highest probability"):
        _usage_and_answers(bad, {key: set(JEv_LABELS) for key in request["questions"]})


@pytest.mark.asyncio
async def test_native_jeveval_uses_one_mocked_opener_request_for_all_criteria(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent: list[dict[str, Any]] = []

    def fake_urlopen(request: Any, timeout: int) -> _HttpResponse:
        assert timeout == 120
        assert request.get_header("Authorization") == "Bearer fake-jev-key"
        payload = json.loads(request.data)
        sent.append(payload)
        return _HttpResponse(json.dumps(_response(payload)).encode())

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    model = OpenRouterJevModel("typesafe/jev-1.14-20261014", "fake-jev-key")
    questions, _, _ = criterion_questions(
        "Q08",
        {
            "required": [
                "Both granite condition checks have no applicable positive facts and remain unknown.",
                "Typed agreements, if extracted, retain BASALT+GNEISS scope.",
            ],
            "forbidden": ["Do not widen scoped facts to household-wide facts."],
        },
    )
    metric = JevEval(
        name="offline_saved_run",
        evaluation_params=[
            SingleTurnParams.INPUT,
            SingleTurnParams.ACTUAL_OUTPUT,
            SingleTurnParams.RETRIEVAL_CONTEXT,
        ],
        questions=questions,
        system_one_model=model,
    )
    score = await metric.a_measure(
        LLMTestCase(
            input="question",
            actual_output="answer",
            retrieval_context=['{"source": "from saved result"}'],
        ),
        _show_indicator=False,
    )
    assert score > 0.9
    assert len(sent) == 1
    assert set(sent[0]["questions"]) == {"q_0", "q_1", "q_2"}
    assert set(sent[0]["questions"]["q_0"]["criteria"]) == set(JEv_LABELS)
    assert set(sent[0]["questions"]["q_1"]["criteria"]) == {*JEv_LABELS, "not_applicable"}
    assert set(sent[0]["questions"]["q_2"]["criteria"]) == set(JEv_LABELS)
    assert model.last_usage == {"input_tokens": 123, "output_tokens": 35, "cost": 0.00002}
    assert metric.input_tokens == 123
    assert metric.output_tokens == 35
    assert metric.score_breakdown is not None
    assert len(metric.score_breakdown) == 3


@pytest.mark.asyncio
async def test_native_jeveval_scores_applicability_and_actual_prohibitions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    answer_examples = {
        "q02_missing_sir": "Madame Obsidian is available and fits the quiet home.",
        "q02_sir_included": "Sir Pebble enjoys quiet evenings; his GRANITE pair conditions remain unconfirmed.",
        "q08_guide_quote": "The GRANITE+GRANITE guide says to rotate small decisions and set a deadline; the conditions are unconfirmed.",
        "q08_household_claim": "Our GRANITE+GRANITE household already agreed to rotate decisions and set a deadline.",
        "q09_silent": "No checked candidates.",
        "q09_cancels_trigger": "Madame Obsidian enjoys people, so she will calmly tolerate the vacuum.",
        "q11_silent": "I could not make a recommendation.",
        "q11_changes_status": "Velvet Slate is RETURNED, but my caregiving experience makes that status irrelevant.",
        "q16_missing_sociability": "Homeward Pumice is AVAILABLE. GRANITE+PUMICE remains CONDITIONAL.",
        "q16_infers_from_sociability": "Homeward Pumice enjoys other stones, so she is compatible with granite and quiet homes.",
        "q17_no_migration": "Sir Pebble's biography says he enjoys quiet evenings.",
        "q17_quote_migration": "Professor Quartzless enjoys quiet evenings.",
        "q07_missing_denial": "The rotating decision is confirmed.",
        "q07_preserves_denial": "Rotation is confirmed, but the deadline was denied; the pair remains unconfirmed.",
        "q18_partial_comparison": "Sir Pebble is AVAILABLE and enjoys quiet evenings.",
        "q18_both_compared": "Sir Pebble is AVAILABLE and enjoys quiet evenings; Professor Quartzless is AVAILABLE but has no quiet-home biography evidence.",
        "q20_mixed_facts": "Limestone likes dry places and dislikes vinegar, so this stone is personally afraid of dampness and vinegar.",
        "q20_separate_facts": "The limestone chapter warns that vinegar damages limestone and persistent dampness is undesirable. Keep it in a dry location. No individual profile supplies personal temperament or conditions.",
    }
    selections = {
        "q02_missing_sir": ["does_not_satisfy", "not_applicable", "not_applicable"],
        "q02_sir_included": ["satisfies", "not_applicable", "not_applicable"],
        "q08_guide_quote": ["satisfies", "not_applicable", "satisfies"],
        "q08_household_claim": ["does_not_satisfy", "does_not_satisfy", "does_not_satisfy"],
        "q09_silent": ["does_not_satisfy", "not_applicable", "satisfies"],
        "q09_cancels_trigger": ["does_not_satisfy", "does_not_satisfy", "does_not_satisfy"],
        "q11_silent": ["does_not_satisfy", "not_applicable", "satisfies"],
        "q11_changes_status": ["does_not_satisfy", "does_not_satisfy", "does_not_satisfy"],
        "q16_missing_sociability": ["does_not_satisfy", "satisfies", "satisfies", "satisfies"],
        "q16_infers_from_sociability": [
            "does_not_satisfy",
            "does_not_satisfy",
            "does_not_satisfy",
        ],
        "q17_no_migration": ["does_not_satisfy", "does_not_satisfy", "not_applicable", "satisfies"],
        "q17_quote_migration": [
            "does_not_satisfy",
            "does_not_satisfy",
            "does_not_satisfy",
            "does_not_satisfy",
        ],
        "q07_missing_denial": ["does_not_satisfy"],
        "q07_preserves_denial": ["satisfies"],
        "q18_partial_comparison": ["does_not_satisfy"],
        "q18_both_compared": ["satisfies"],
        "q20_mixed_facts": ["does_not_satisfy"],
        "q20_separate_facts": ["satisfies"],
    }
    expected_by_case = {
        "q02": {
            "required": [
                "Sir Pebble has biography support but the granite pair conditions are unconfirmed.",
                "Homeward Pumice has no individual quiet-home evidence; Professor's generic biography does not establish it.",
                "Svetlana's individual biography describes loud early-morning singing; it does not support a quiet-home requirement. If she is evaluated, preserve that conflict.",
            ],
            "forbidden": [],
        },
        "q08": {
            "required": [
                "Both granite condition checks have no applicable positive facts and remain unknown.",
                "Typed agreements, if extracted, retain BASALT+GNEISS scope.",
            ],
            "forbidden": ["Do not widen scoped facts to household-wide facts."],
        },
        "q09": {
            "required": [
                "Madame's trigger_notes contradict the vacuum requirement.",
                "If evaluated, exclude her for the unmet requirement even though she enjoys human company.",
            ],
            "forbidden": ["Positive socialization must not cancel the mandatory trigger conflict."],
        },
        "q11": {
            "required": [
                "Velvet Slate cannot be recommended because current status is RETURNED.",
                "If assessed, trigger_notes contradict the loud-music requirement.",
            ],
            "forbidden": [
                "Caregiver experience does not change adoption status or erase a trigger."
            ],
        },
        "q16": {
            "required": [
                "Homeward Pumice is AVAILABLE and ENJOYS_OTHER_STONES is profile evidence for general sociability.",
                "GRANITE+PUMICE stays CONDITIONAL with unmarked conditions.",
                "Individual granite-specific compatibility findings remain empty unless explicit source evidence exists.",
            ],
            "forbidden": [
                "Do not infer quiet-home suitability, granite-specific preference, or completed accommodations from sociability."
            ],
        },
        "q17": {
            "required": [
                "Sir Pebble has qualifying biography evidence; Professor Quartzless does not.",
                "Professor is GRANITE despite Quartzless in the name.",
                "If Professor is evaluated, the required character evidence remains unknown.",
            ],
            "forbidden": [
                "No biography quote may migrate between these stones.",
                "Event frequency is not evidence strength under the current assessment source policy.",
            ],
        },
        "q07": {
            "required": [],
            "forbidden": [
                "Do not silently drop the denial or describe both conditions as fulfilled."
            ],
        },
        "q18": {
            "required": [],
            "forbidden": ["Do not accept a partial single-name answer as a passing comparison."],
        },
        "q20": {
            "required": [],
            "forbidden": ["Keep geological care facts separate from fictional temperament."],
        },
    }
    sent_answers: list[str] = []

    def fake_urlopen(request: Any, timeout: int) -> _HttpResponse:
        assert timeout == 120
        payload = json.loads(request.data)
        payload_text = json.dumps(payload, ensure_ascii=False)
        answer_id = next(key for key, answer in answer_examples.items() if answer in payload_text)
        sent_answers.append(answer_id)
        response = _response(payload)
        for index, choice in enumerate(selections[answer_id]):
            key = f"q_{index}"
            labels = tuple(payload["questions"][key]["criteria"])
            assert choice in labels
            response["answers"][key]["choice"] = choice
            response["answers"][key]["probabilities"] = {
                label: 1.0 if label == choice else 0.0 for label in labels
            }
        return _HttpResponse(json.dumps(response).encode())

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    model = OpenRouterJevModel("typesafe/jev-1.14-20261014", "fake-jev-key")

    async def score_answer(answer_id: str, case_id: str) -> list[dict[str, Any]]:
        questions, criteria, _ = criterion_questions(case_id.upper(), expected_by_case[case_id])
        metric = JevEval(
            name=f"offline_applicability_{answer_id}",
            evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT],
            questions=questions,
            system_one_model=model,
        )
        await metric.a_measure(
            LLMTestCase(
                input="evaluate this saved answer", actual_output=answer_examples[answer_id]
            ),
            _show_indicator=False,
        )
        assert metric.score_breakdown is not None
        assert len(metric.score_breakdown) == len(criteria)
        return metric.score_breakdown

    outcomes = {
        answer_id: await score_answer(answer_id, case_id)
        for case_id, answer_ids in {
            "q02": ["q02_missing_sir", "q02_sir_included"],
            "q08": ["q08_guide_quote", "q08_household_claim"],
            "q09": ["q09_silent", "q09_cancels_trigger"],
            "q11": ["q11_silent", "q11_changes_status"],
            "q16": ["q16_missing_sociability", "q16_infers_from_sociability"],
            "q17": ["q17_no_migration", "q17_quote_migration"],
            "q07": ["q07_missing_denial", "q07_preserves_denial"],
            "q18": ["q18_partial_comparison", "q18_both_compared"],
            "q20": ["q20_mixed_facts", "q20_separate_facts"],
        }.items()
        for answer_id in answer_ids
    }
    assert sent_answers == list(answer_examples)
    assert outcomes["q02_missing_sir"][0]["probabilities"]["does_not_satisfy"] == 1.0
    assert outcomes["q02_sir_included"][0]["probabilities"]["satisfies"] == 1.0
    assert outcomes["q08_guide_quote"][1]["applicable"] is False
    assert outcomes["q08_household_claim"][1]["probabilities"]["does_not_satisfy"] == 1.0
    assert outcomes["q09_silent"][2]["probabilities"]["satisfies"] == 1.0
    assert outcomes["q09_cancels_trigger"][2]["probabilities"]["does_not_satisfy"] == 1.0
    assert outcomes["q11_silent"][2]["probabilities"]["satisfies"] == 1.0
    assert outcomes["q11_changes_status"][2]["probabilities"]["does_not_satisfy"] == 1.0
    assert outcomes["q16_missing_sociability"][0]["probabilities"]["does_not_satisfy"] == 1.0
    assert outcomes["q16_infers_from_sociability"][1]["probabilities"]["does_not_satisfy"] == 1.0
    assert outcomes["q17_no_migration"][3]["probabilities"]["satisfies"] == 1.0
    assert outcomes["q17_quote_migration"][3]["probabilities"]["does_not_satisfy"] == 1.0
    assert outcomes["q07_missing_denial"][0]["probabilities"]["does_not_satisfy"] == 1.0
    assert outcomes["q07_preserves_denial"][0]["probabilities"]["satisfies"] == 1.0
    assert outcomes["q18_partial_comparison"][0]["probabilities"]["does_not_satisfy"] == 1.0
    assert outcomes["q18_both_compared"][0]["probabilities"]["satisfies"] == 1.0
    assert outcomes["q20_mixed_facts"][0]["probabilities"]["does_not_satisfy"] == 1.0
    assert outcomes["q20_separate_facts"][0]["probabilities"]["satisfies"] == 1.0


def test_safe_archive_redacts_keys_and_filename_slug_uses_model() -> None:
    value = {"model": "typesafe/jev-1.14", "nested": ["fake-jev-key"]}
    assert sanitize_payload(value, "fake-jev-key")["nested"] == ["[redacted]"]
    assert _model_slug("typesafe/jev-1.14-20261014") == "typesafe-jev-1-14-20261014"
