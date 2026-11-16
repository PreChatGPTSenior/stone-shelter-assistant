"""DeepEval Jev adapter and archived-answer preparation for saved scenario runs."""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import urllib.request
from math import isclose
from typing import Any

from deepeval.metrics.jev_eval.questions import Choice
from deepeval.models import DeepEvalBaseSystemOneModel
from deepeval.models.system_one.schema import (
    ChoiceAnswer,
    ChoiceQuestion,
    SystemOneAnswers,
    SystemOneQuestion,
)
from deepeval.models.utils import EvaluationCost

JEv_ENDPOINT = "https://openrouter.ai/api/alpha/decisions"
JEv_LABELS = ("satisfies", "partially_satisfies", "does_not_satisfy")
JEv_LABEL_DESCRIPTIONS = {
    "satisfies": "The answer clearly satisfies the reviewed criterion.",
    "partially_satisfies": "The answer addresses the criterion but is incomplete or qualified incorrectly.",
    "does_not_satisfy": "The answer fails the criterion or commits the prohibited behavior.",
    "substantive": "The answer provides a substantive, useful response to the request.",
    "partial_but_useful": "The answer provides some useful response, though it is incomplete.",
    "clarification_or_error_only": "The answer only requests clarification, refuses, or provides no usable finding.",
    "not_applicable": "The final answer does not meet the stated condition for judging this criterion.",
}


ANSWER_CRITERION_REWRITES = {
    "Q03": {
        "Retrieve Sir Pebble; his biography supports the quiet-home requirement.": "Sir Pebble is presented as a quiet-home fit and the answer's supporting source is his own biography.",
    },
    "Q10": {
        "Retrieve Brave Gneiss and verify AVAILABLE.": "The answer identifies Brave Gneiss as AVAILABLE, with the status claim supported by the saved source records.",
    },
    "Q04": {
        "The authored verdict stays CONDITIONAL; its conditions_status becomes confirmed.": "The answer preserves the authored CONDITIONAL verdict and explains that both conditions are confirmed.",
    },
    "Q06": {
        "No positive established agreement may be extracted.": "The answer does not state that either shared decision agreement has already been established.",
    },
    "Q08": {
        "Both granite condition checks have no applicable positive facts and remain unknown.": "For GRANITE+GRANITE, does the final answer state that both decision-rotation and deadline checks remain unknown? A guide's prescribed agreement is not evidence that the household already made that agreement.",
    },
}
ANSWER_CRITERION_CONDITIONALS = {
    "Q02": {
        "Homeward Pumice has no individual quiet-home evidence; Professor's generic biography does not establish it.": "If the final answer discusses Homeward Pumice or Professor Quartzless as quiet-home options, does it avoid claiming that their cited evidence establishes quiet-home suitability? Select not_applicable when neither is discussed as an option.",
        "Svetlana's individual biography describes loud early-morning singing; it does not support a quiet-home requirement. If she is evaluated, preserve that conflict.": "If the final answer evaluates Svetlana for a quiet home, does it preserve that her biography describes loud early-morning singing? Select not_applicable when she is not evaluated.",
    },
    "Q08": {
        "Typed agreements, if extracted, retain BASALT+GNEISS scope.": "If the final answer says a household agreement has already been made, does it keep that agreement scoped to BASALT+GNEISS and avoid applying it to GRANITE+GRANITE? A quoted guide rule or proposal is not an accomplished agreement. Select not_applicable if the answer reports no established agreement.",
    },
    "Q09": {
        "If evaluated, exclude her for the unmet requirement even though she enjoys human company.": "If the final answer evaluates or recommends Madame Obsidian, does it exclude her because her trigger_notes conflict with the mandatory vacuum requirement, even though she enjoys human company? Select not_applicable if Madame is not evaluated or recommended.",
    },
    "Q11": {
        "If assessed, trigger_notes contradict the loud-music requirement.": "If the final answer evaluates or recommends Velvet Slate, does it state that her trigger_notes conflict with the mandatory loud-music requirement? Select not_applicable if Velvet Slate is not evaluated or recommended.",
    },
    "Q17": {
        "If Professor is evaluated, the required character evidence remains unknown.": "If the final answer evaluates Professor Quartzless for quiet-home suitability, does it leave the required individual character evidence unknown unless explicit individual evidence is cited? Select not_applicable if Professor is not evaluated.",
    },
}
ANSWER_CRITERION_NO_VIOLATION = {
    "Q08": {
        "Do not widen scoped facts to household-wide facts.": "Does the final answer avoid claiming that a scoped fact applies household-wide? Quoting a source rule with its pair scope is not widening a household fact.",
    },
    "Q09": {
        "Positive socialization must not cancel the mandatory trigger conflict.": "Does the final answer avoid using positive socialization to cancel the mandatory trigger conflict? If it does not make that claim, the prohibition is satisfied; judge only claims actually present in the answer.",
    },
    "Q11": {
        "Caregiver experience does not change adoption status or erase a trigger.": "Does the final answer avoid claiming that caregiver experience changes adoption status or erases a trigger? If it makes no such claim, the prohibition is satisfied; judge only claims actually present in the answer.",
    },
    "Q16": {
        "Individual granite-specific compatibility findings remain empty unless explicit source evidence exists.": "If the final answer makes a granite-specific compatibility claim, is it supported by explicit individual evidence? Select not_applicable when it makes no such claim.",
        "Do not infer quiet-home suitability, granite-specific preference, or completed accommodations from sociability.": "Does the final answer avoid claiming quiet-home suitability, granite-specific preference, or completed accommodations based only on sociability? If it makes no such claim, the prohibition is satisfied; judge only claims actually present in the answer.",
    },
    "Q17": {
        "No biography quote may migrate between these stones.": "Does the final answer avoid assigning one stone's biography quote to another stone? If it does not do so, the prohibition is satisfied; judge only claims actually present in the answer.",
    },
}
ANSWER_CRITERION_OMISSION_SENSITIVE = {
    "Q07": {
        "Do not silently drop the denial or describe both conditions as fulfilled.": "Does the final answer preserve that rotation is confirmed but the deadline is contradicted, and avoid describing both conditions as fulfilled? Omitting the denial is a failure of this completeness criterion.",
    },
    "Q18": {
        "Do not accept a partial single-name answer as a passing comparison.": "Does the final answer compare both Sir Pebble and Professor Quartzless? A single-name or empty answer does not satisfy this completeness criterion.",
    },
    "Q20": {
        "Keep geological care facts separate from fictional temperament.": "Does the final answer give geological care facts separately from fictional temperament claims? Omitting the required distinction or presenting them as the same kind of evidence does not satisfy this criterion.",
    },
}
UNMEASURED_STAGE_CRITERIA = {
    "Q02": {
        (
            "forbidden",
            "Do not require one fixed shortlist or order before inspecting retrieval.",
        ): "This is a retrieval-evaluation policy, not a final-answer claim.",
    },
    "Q09": {
        (
            "required",
            "If no candidate is returned, separately score retrieval so an empty shortlist cannot masquerade as successful evaluation.",
        ): "This requires a separate retrieval metric and cannot be judged from the final answer.",
    },
    "Q17": {
        (
            "forbidden",
            "Event frequency is not evidence strength under the current assessment source policy.",
        ): "This is an evidence-assessment policy, not a final-answer claim.",
    },
}


def criterion_questions(
    case_id: str, expected: dict[str, Any]
) -> tuple[list[Choice], list[dict[str, Any]], list[dict[str, str]]]:
    """Create one Jev choice per reviewed required or forbidden answer criterion."""
    questions: list[Choice] = []
    criteria: list[dict[str, Any]] = []
    options = {"satisfies": 1.0, "partially_satisfies": 0.5, "does_not_satisfy": 0.0}
    answer_only = (
        "Judge the final answer text only for whether it states or avoids this criterion. "
        "Use the supplied sources only to verify factual support and scope; source presence "
        "alone does not mean the answer included the claim. Do not grade retrieval, parsing, "
        "structured extraction, or evaluation procedure. An omitted required positive "
        "statement does not satisfy the criterion. For a prohibition about a claim or act, "
        "silence complies and does_not_satisfy requires an actual prohibited claim or act. "
        "A reviewed criterion may explicitly require preserving or including information; "
        "omission then fails that stated completeness requirement. "
    )
    unmeasured: list[dict[str, str]] = []
    for direction, key, instruction in (
        ("required", "required", "Does the final answer satisfy this required criterion?"),
        ("forbidden", "forbidden", "Does the final answer comply with this prohibition?"),
    ):
        items = expected.get(key, [])
        if not isinstance(items, list):
            raise ValueError(f"Scenario expected.{key} must be a list")
        for index, text in enumerate(items, start=1):
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"Scenario expected.{key}[{index - 1}] must be non-empty text")
            if (
                reason := UNMEASURED_STAGE_CRITERIA.get(case_id, {}).get((direction, text))
            ) is not None:
                unmeasured.append(
                    {
                        "id": f"{direction}-{index}",
                        "direction": direction,
                        "source_text": text,
                        "status": "not_measured",
                        "reason": reason,
                    }
                )
                continue
            judge_text = ANSWER_CRITERION_REWRITES.get(case_id, {}).get(text, text)
            conditional_text = ANSWER_CRITERION_CONDITIONALS.get(case_id, {}).get(text)
            no_violation_text = ANSWER_CRITERION_NO_VIOLATION.get(case_id, {}).get(text)
            omission_sensitive_text = ANSWER_CRITERION_OMISSION_SENSITIVE.get(case_id, {}).get(text)
            judge_text = (
                conditional_text or omission_sensitive_text or no_violation_text or judge_text
            )
            not_applicable_option = (
                {"not_applicable": None}
                if conditional_text is not None
                or (no_violation_text is not None and "not_applicable" in no_violation_text)
                or (
                    case_id == "Q14"
                    and text == "If discussing history, reservation ended after reservation began."
                )
                else {}
            )
            if (
                case_id == "Q14"
                and text == "If discussing history, reservation ended after reservation began."
            ):
                judge_text = (
                    "If the final answer discusses reservation history, does it state that the "
                    "reservation ended after it began? Select not_applicable when the final "
                    "answer does not discuss reservation history; do not infer the chronology "
                    "from sources that the answer did not mention."
                )
            criteria.append(
                {
                    "id": f"{direction}-{index}",
                    "direction": direction,
                    "source_text": text,
                    "text": judge_text,
                    **({"applicability_option": "not_applicable"} if not_applicable_option else {}),
                }
            )
            questions.append(
                Choice(
                    question=f"{answer_only}{instruction} Reviewed criterion: {judge_text}",
                    options={**options, **not_applicable_option},
                )
            )
    if case_id == "Q06":
        gate_question = (
            "Does the final answer provide any useful, substantive response to the user's "
            "recommendation request, even if it appropriately describes a candidate as "
            "conditional? Choose clarification_or_error_only only when the answer merely "
            "asks the user to restate the request, refuses, or gives no usable finding."
        )
        questions.append(
            Choice(
                question=gate_question,
                options={
                    "substantive": 1.0,
                    "partial_but_useful": 0.5,
                    "clarification_or_error_only": 0.0,
                },
            )
        )
        criteria.append(
            {
                "id": "answer-substance-gate",
                "direction": "required_gate",
                "source_text": "Provide a substantive, useful response rather than only a clarification or error message.",
                "text": gate_question,
                "gate": True,
            }
        )
    if not questions:
        raise ValueError("Saved case has no reviewed required or forbidden answer criteria")
    return questions, criteria, unmeasured


SCORE_THRESHOLD_TOLERANCE = 1e-12


def score_meets_threshold(score: float, threshold: float) -> bool:
    """Compare scores with a tiny float tolerance while retaining the raw score."""
    return score >= threshold or isclose(
        score, threshold, rel_tol=0.0, abs_tol=SCORE_THRESHOLD_TOLERANCE
    )


def criterion_gates_pass(
    criteria: list[dict[str, Any]], outcomes: list[dict[str, Any]]
) -> tuple[bool, list[dict[str, Any]]]:
    """Apply required gates independently of the averaged Jev score."""
    gates: list[dict[str, Any]] = []
    for criterion, outcome in zip(criteria, outcomes, strict=True):
        if not criterion.get("gate"):
            continue
        probabilities = outcome.get("probabilities", {})
        selected = max(probabilities, key=probabilities.get) if probabilities else None
        passed = selected in {"substantive", "partial_but_useful"}
        gates.append({"id": criterion["id"], "selected": selected, "passed": passed})
    return all(gate["passed"] for gate in gates), gates


def _usage_and_answers(
    response: Any, question_options: dict[str, set[str]]
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(response, dict) or not isinstance(response.get("answers"), dict):
        raise ValueError("Jev response must contain an answers object")
    answers = response["answers"]
    if set(answers) != set(question_options):
        raise ValueError("Jev response answer keys do not match the requested questions")
    safe_answers: dict[str, Any] = {}
    choices: dict[str, ChoiceAnswer] = {}
    for key, answer in answers.items():
        if not isinstance(answer, dict) or answer.get("type") != "choice":
            raise ValueError(f"Jev answer {key} must have type choice")
        probabilities = answer.get("probabilities")
        expected_options = question_options[key]
        if (
            not expected_options
            or not isinstance(probabilities, dict)
            or set(probabilities) != expected_options
        ):
            raise ValueError(f"Jev answer {key} must include all choice probabilities")
        if (
            any(
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(value)
                or not 0 <= value <= 1
                for value in probabilities.values()
            )
            or abs(sum(probabilities.values()) - 1) > 0.02
        ):
            raise ValueError(f"Jev answer {key} has invalid probabilities")
        choice = answer.get("choice")
        confidence = answer.get("confidence")
        highest_probability = max(probabilities, key=lambda label: float(probabilities[label]))
        if choice not in expected_options or choice != highest_probability:
            raise ValueError(f"Jev answer {key} choice does not match the highest probability")
        if (
            not isinstance(confidence, (int, float))
            or isinstance(confidence, bool)
            or not math.isfinite(confidence)
            or not 0 <= confidence <= 1
        ):
            raise ValueError(f"Jev answer {key} confidence must be in [0, 1]")
        safe_answers[key] = {
            "type": "choice",
            "choice": choice,
            "confidence": confidence,
            "probabilities": probabilities,
        }
        choices[key] = ChoiceAnswer(
            choice=choice, confidence=confidence, probabilities=probabilities
        )
    usage = response.get("usage")
    if not isinstance(usage, dict):
        raise ValueError("Jev response must include usage")
    for name in ("input_tokens", "output_tokens"):
        if not isinstance(usage.get(name), int) or isinstance(usage[name], bool) or usage[name] < 0:
            raise ValueError(f"Jev usage.{name} must be a non-negative integer")
    cost = usage.get("cost")
    if (
        not isinstance(cost, (int, float))
        or isinstance(cost, bool)
        or not math.isfinite(cost)
        or cost < 0
    ):
        raise ValueError("Jev usage.cost must be finite and non-negative")
    safe_usage = {
        "input_tokens": usage["input_tokens"],
        "output_tokens": usage["output_tokens"],
        "cost": cost,
    }
    return {"choices": choices, "usage": safe_usage}, safe_answers


class OpenRouterJevModel(DeepEvalBaseSystemOneModel):
    """DeepEval's native System One adapter, using the explicitly configured OpenRouter endpoint."""

    def __init__(self, model: str, api_key: str) -> None:
        self.model_id = model
        self.api_key = api_key
        self.last_request: dict[str, Any] | None = None
        self.last_safe_response: dict[str, Any] | None = None
        self.last_response_sha256: str | None = None
        self.last_usage: dict[str, Any] | None = None
        super().__init__(model)

    def load_model(self, *args: Any, **kwargs: Any) -> OpenRouterJevModel:
        return self

    def get_model_name(self, *args: Any, **kwargs: Any) -> str:
        return self.model_id

    def _request_payload(
        self, state: Any, questions: dict[str, SystemOneQuestion]
    ) -> dict[str, Any]:
        return {
            "model": self.model_id,
            "state": state,
            "questions": {
                key: {
                    "type": "choice",
                    "instructions": question.instructions,
                    "criteria": {
                        label: JEv_LABEL_DESCRIPTIONS.get(
                            label, "This answer option applies to the reviewed criterion."
                        )
                        for label in _choice_options(question)
                    },
                }
                for key, question in questions.items()
            },
        }

    def _post(self, payload: dict[str, Any]) -> tuple[SystemOneAnswers, EvaluationCost]:
        self.last_request = None
        self.last_safe_response = None
        self.last_response_sha256 = None
        self.last_usage = None
        self.last_request = payload
        request_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            JEv_ENDPOINT,
            data=request_bytes,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            body = response.read()
        self.last_response_sha256 = hashlib.sha256(body).hexdigest()
        parsed = json.loads(body)
        question_options = {
            key: set(question["criteria"]) for key, question in payload["questions"].items()
        }
        parsed_answers, safe_answers = _usage_and_answers(parsed, question_options)
        usage = parsed_answers["usage"]
        model = parsed.get("model") if isinstance(parsed, dict) else None
        self.last_safe_response = {
            **({"model": model[:120]} if isinstance(model, str) else {}),
            "answers": safe_answers,
            "usage": usage,
        }
        self.last_usage = usage
        return (
            SystemOneAnswers(choices=parsed_answers["choices"]),
            EvaluationCost(usage["cost"], usage["input_tokens"], usage["output_tokens"]),
        )

    def decide(
        self, state: Any, questions: dict[str, SystemOneQuestion]
    ) -> tuple[SystemOneAnswers, EvaluationCost]:
        return self._post(self._request_payload(state, questions))

    async def a_decide(
        self, state: Any, questions: dict[str, SystemOneQuestion]
    ) -> tuple[SystemOneAnswers, EvaluationCost]:
        return await asyncio.to_thread(self.decide, state, questions)


def sanitize_payload(value: Any, api_key: str) -> Any:
    """Redact credentials from the retained request and error data."""
    if isinstance(value, str):
        return value.replace(api_key, "[redacted]")
    if isinstance(value, list):
        return [sanitize_payload(item, api_key) for item in value]
    if isinstance(value, dict):
        return {key: sanitize_payload(item, api_key) for key, item in value.items()}
    return value


def _choice_options(question: SystemOneQuestion) -> dict[str, Any]:
    if not isinstance(question, ChoiceQuestion):
        raise TypeError("Saved-run Jev adapter only supports choice questions")
    return question.options
