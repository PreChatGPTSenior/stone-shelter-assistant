"""Opt-in paid replay: RUN_OPENROUTER_EVALUATION=1 uv run pytest -s tests/live."""

import asyncio
import json
import os
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from time import monotonic
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from langchain_core.messages import AIMessage, convert_to_messages
from langchain_openrouter import ChatOpenRouter
from langfuse import Evaluation, Langfuse, propagate_attributes

from stone_shelter_assistant.assistant.candidate_assessment import evaluate_candidate
from stone_shelter_assistant.assistant.candidate_criteria import SearchCriteria
from stone_shelter_assistant.assistant.candidate_evidence import (
    CandidateEvidence,
    candidate_sources,
)
from stone_shelter_assistant.assistant.tracing import WorkflowTraceHandler
from stone_shelter_assistant.assistant.workflow import model_call_details, structured_model
from stone_shelter_assistant.core.settings import LangfuseSettings, OpenRouterSettings
from stone_shelter_assistant.search.document_models import (
    CompatibilityPairSearchDocument,
    EncyclopediaSectionSearchDocument,
)
from stone_shelter_assistant.stones.stone_contracts import StoneDetails

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_OPENROUTER_EVALUATION") != "1", reason="Explicit live-model opt-in required"
)
SNAPSHOT = Path(__file__).parents[1] / "fixtures/assistant/quiet-home-assessment.json"
MODELS = (
    ("openai/gpt-6-luna", "medium"),
    ("deepseek/deepseek-v4.1-flash", "high"),
    ("anthropic/claude-sonnet-5", "medium"),
    ("google/gemini-3.8-flash", "medium"),
    ("openai/gpt-6.1-terra", "medium"),
    ("dots-studio/dots-3-note-preview:free", "medium"),
)
CHECKS = ("dto_valid", "evidence_grounded", "character_coverage", "no_invented_compatibility")


def check_assessment(assessment: CandidateEvidence, snapshot: dict[str, Any]) -> dict[str, Any]:
    """Check source grounding and the explicit facts of this frozen scenario."""
    criteria = SearchCriteria.model_validate(snapshot["criteria"])
    cards = [StoneDetails.model_validate(value) for value in snapshot["cards"]]
    documents = snapshot["documents"].values()
    chapters = {
        value["stone_types"][0]: EncyclopediaSectionSearchDocument.model_validate(value)
        for value in documents
        if value.get("document_kind") == "encyclopedia_section"
    }
    pairs = {
        value["pair_key"]: CompatibilityPairSearchDocument.model_validate(value)
        for value in snapshot["documents"].values()
        if value.get("document_kind") == "compatibility_pair"
    }
    sources = json.loads(snapshot["messages"][1]["content"])["candidate_sources"]
    supplied = {(item["stone_id"], item["source_ref"]): item["text"] for item in sources}
    criterion_fragments = {
        criterion.criterion_id: criterion.fragment_id
        for criterion in (*criteria.requirements.character, *criteria.preferences.character)
    }
    grounded = all(
        (finding.stone_id, finding.source_ref) in supplied
        and finding.quote in supplied[(finding.stone_id, finding.source_ref)]
        for finding in (*assessment.character, *assessment.individual_compatibility)
    ) and all(
        finding.criterion_id in criterion_fragments
        and finding.fragment_id == criterion_fragments[finding.criterion_id]
        for finding in assessment.character
    )
    covered = {
        (finding.stone_id, finding.criterion_id)
        for finding in assessment.character
        if finding.finding == "confirmed"
        and finding.criterion_id in criterion_fragments
        and finding.fragment_id == criterion_fragments[finding.criterion_id]
    }
    expected_coverage = {
        (str(card.id), criterion_id)
        for card in cards
        for criterion_id in criterion_fragments
    }
    evaluations = [
        evaluate_candidate(
            criteria,
            card,
            snapshot["verified_statuses"][str(card.id)],
            pairs,
            candidate_sources(card, chapters.get(card.stone_type)),
            assessment,
            "parsed",
        ).model_dump(mode="json")
        for card in cards
    ]
    # Both biographies explicitly describe quiet/peaceful homes. Neither card states
    # a preference for granite, and no household fact establishes conditional arrangements.
    return {
        "dto_valid": True,
        "evidence_grounded": grounded,
        "character_coverage": covered == expected_coverage,
        "no_invented_compatibility": not assessment.individual_compatibility,
        "candidate_evaluations": evaluations,
        "assessment": assessment.model_dump(mode="json"),
    }


def score_checks(*, output: Any, **kwargs: Any) -> list[Evaluation]:
    return [Evaluation(name=name, value=float(bool(output.get(name)))) for name in CHECKS]


@pytest.mark.asyncio
async def test_frozen_assessment_across_models() -> None:
    snapshot = json.loads(SNAPSHOT.read_text())
    assert snapshot["schema"] == CandidateEvidence.model_json_schema()
    version = sha256(SNAPSHOT.read_bytes()).hexdigest()
    settings = LangfuseSettings()
    client = Langfuse(
        public_key=settings.public_key,
        secret_key=settings.secret_key.get_secret_value(),
        base_url=settings.base_url,
    )
    dataset_name = "PY-037/quiet-home-candidate-assessment"
    client.create_dataset(name=dataset_name, description="Frozen evidence from a failed Dots call")
    dataset_item = client.create_dataset_item(
        dataset_name=dataset_name,
        id=f"py-037-{version[:24]}",
        input=snapshot,
        expected_output={
            "confirmed_character_names": [card["name"] for card in snapshot["cards"]],
            "individual_compatibility": [],
        },
        metadata={"snapshot_sha256": version, "fixture_version": snapshot["fixture_version"]},
    )
    api_key = OpenRouterSettings().api_key
    now = datetime.now(ZoneInfo("Asia/Tbilisi"))
    batch = now.strftime("%Y%m%dT%H%M%S")
    semaphore = asyncio.Semaphore(2)

    async def run_model(model_id: str, effort: str) -> dict[str, Any]:
        async def task(*, item: Any, **kwargs: Any) -> dict[str, Any]:
            client.update_current_span(
                input={"dataset_item_id": item.id, "snapshot_sha256": version}
            )
            summary: dict[str, Any] = {
                "model_id": model_id,
                "requested_reasoning": effort,
                "max_tokens": 8192,
                **dict.fromkeys(CHECKS, False),
            }
            with (
                propagate_attributes(
                    user_id="local-test-user", session_id=f"{now:%Y-%m-%d}-PY-037"
                ),
                client.start_as_current_observation(name="evaluate_candidates") as stage,
            ):
                started = monotonic()
                try:
                    model = ChatOpenRouter(
                        model_name=model_id,
                        openrouter_api_key=api_key,
                        max_tokens=8192,
                        max_retries=0,
                        request_timeout=180_000,
                    )
                    _, runnable = structured_model(
                        model,
                        CandidateEvidence,
                        use_json_schema=True,
                        reasoning={"effort": effort},
                    )
                    callback = WorkflowTraceHandler(
                        public_key=settings.public_key,
                        trace_context={"trace_id": stage.trace_id, "parent_span_id": stage.id},
                    )
                    response = await runnable.ainvoke(
                        convert_to_messages(item.input["messages"]),
                        config={"callbacks": [callback]},
                    )
                    if isinstance(response, dict):
                        raw = response.get("raw")
                        if isinstance(raw, AIMessage):
                            summary["model_call"] = model_call_details(raw)
                        parsed = response.get("parsed")
                        if isinstance(parsed, CandidateEvidence):
                            summary.update(check_assessment(parsed, item.input))
                        elif response.get("parsing_error"):
                            summary["error"] = str(response["parsing_error"]).split("\n")[0][:300]
                except Exception as error:
                    summary["error"] = f"{type(error).__name__}: {error}"[:600]
                    if isinstance(body := getattr(error, "body", None), str):
                        summary["provider_error"] = body[:1500]
                summary["seconds"] = round(monotonic() - started, 2)
                summary["passed"] = all(summary[name] for name in CHECKS)
                stage.update(output=summary)
                return summary

        async with semaphore:
            with propagate_attributes(
                user_id="local-test-user", session_id=f"{now:%Y-%m-%d}-PY-037"
            ):
                experiment = await asyncio.to_thread(
                    client.run_experiment,
                    name=dataset_name,
                    run_name=f"{batch}-{model_id.replace('/', '-')}",
                    data=[dataset_item],
                    task=task,
                    evaluators=[score_checks],
                    max_concurrency=1,
                    metadata={
                        "model_id": model_id,
                        "reasoning": effort,
                        "max_tokens": "8192",
                        "snapshot_sha256": version,
                    },
                )
        result: dict[str, Any] = experiment.item_results[0].output
        result["trace_id"] = experiment.item_results[0].trace_id
        result["experiment_url"] = experiment.experiment_url
        print("RESULT", json.dumps(result, ensure_ascii=False), flush=True)
        return result

    selected_model = os.getenv("OPENROUTER_EVALUATION_MODEL")
    cases = [case for case in MODELS if selected_model is None or case[0] == selected_model]
    assert cases, f"Unknown evaluation model: {selected_model}"
    results = await asyncio.gather(*(run_model(model, effort) for model, effort in cases))
    await asyncio.to_thread(client.flush)
    assert all(result["passed"] for result in results), [
        {
            "model": result["model_id"],
            "error": result.get("error"),
            "failed_checks": [name for name in CHECKS if not result[name]],
        }
        for result in results
        if not result["passed"]
    ]
