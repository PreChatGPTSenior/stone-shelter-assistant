"""Check answer generation accepts only explanations bound to each candidate source."""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from langgraph.runtime import Runtime

from stone_shelter_assistant.assistant import workflow
from stone_shelter_assistant.assistant.candidate_assessment import (
    CandidateEvaluation,
    Reason,
)
from stone_shelter_assistant.assistant.candidate_evidence import (
    Evidence,
)
from stone_shelter_assistant.search.document_models import CompatibilityPairSearchDocument
from stone_shelter_assistant.search.knowledge.stone_compatibility_document_builder import (
    build_stone_compatibility_documents,
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("case", "expected_prose_ids"),
    [
        ("card", {"stone-a", "stone-b"}),
        ("observations", {"stone-a", "stone-b"}),
        ("cross_candidate", {"stone-a"}),
        ("unknown", {"stone-a"}),
        ("mixed_good_bad", {"stone-b"}),
        ("empty", {"stone-b"}),
        ("shared_encyclopedia", {"stone-a", "stone-b"}),
        ("shared_compatibility", {"stone-a", "stone-b"}),
    ],
)
@pytest.mark.acceptance("AC-ANSWER-01")
async def test_answer_accepts_only_per_candidate_bound_explanations(
    monkeypatch: pytest.MonkeyPatch,
    case: str,
    expected_prose_ids: set[str],
) -> None:
    monkeypatch.setattr(workflow, "get_config", lambda: {})
    ids = {"stone-a": str(uuid4()), "stone-b": str(uuid4())}
    event_ids = {"stone-a": "event-a", "stone-b": "event-b"}
    shared_id = "encyclopedia:en:granite"
    shared_evidence = Evidence(
        source_id=shared_id,
        field="text",
        source_kind="encyclopedia",
        priority=4,
        weight=0.5,
        supports_requirement=False,
        finding="confirmed",
        quote="Granite is generally steady.",
    )
    pair_document = None
    if case == "shared_compatibility":
        guide_path = "fixtures/knowledge/type-compatibility/stone-type-compatibility_en.json"
        documents = build_stone_compatibility_documents(
            (Path(__file__).parents[3] / guide_path).read_text(), guide_path
        )
        pair_document = next(
            document
            for document in documents
            if isinstance(document, CompatibilityPairSearchDocument)
            and document.pair_key == "GRANITE+GRANITE"
        )
        pair_evidence = Evidence(
            source_id=pair_document.source_key,
            field="verdict",
            source_kind="compatibility_pair",
            priority=1,
            weight=1.0,
            supports_requirement=True,
            finding="confirmed",
        )
    event_sources: dict[str, dict[str, object]] = {
        f"case-event:{event_ids[name]}": {
            "tool": "get_case_timeline",
            "data": {"event_notes": f"{name} observation quote."},
        }
        for name in ids
    }
    evaluation_sources: dict[str, dict[str, object]] = {
        **event_sources,
        shared_id: {
            "tool": "search_knowledge_lexical",
            "data": {"text": "Granite is generally steady."},
        },
    }
    if pair_document is not None:
        evaluation_sources[pair_document.source_key] = {
            "tool": "get_compatibility_pair",
            "data": pair_document.model_dump(mode="json"),
        }
    candidate_evaluations = []
    for name in ids:
        own_evidence = Evidence(
            source_id=f"case-event:{event_ids[name]}",
            field="event_notes",
            source_kind="observation",
            priority=2,
            weight=0.95,
            supports_requirement=True,
            finding="confirmed",
            quote=f"{name} observation quote.",
        )
        reason_evidence = [own_evidence]
        if case == "shared_encyclopedia":
            reason_evidence.append(shared_evidence)
        reasons = [
            Reason(
                criterion="availability",
                finding="confirmed",
                required=True,
                source_id="verified_statuses",
                status="AVAILABLE",
            ),
            Reason(
                criterion="character",
                finding="confirmed",
                required=True,
                question_quote="Prefer a calm companion.",
                evidence=reason_evidence,
                chosen_evidence=own_evidence,
            ),
        ]
        if pair_document is not None:
            reasons.append(
                Reason(
                    criterion="compatibility",
                    finding="confirmed",
                    required=False,
                    source_id=pair_document.source_key,
                    pair_key=pair_document.pair_key,
                    verdict=pair_document.verdict,
                    evidence=[pair_evidence],
                    chosen_evidence=pair_evidence,
                )
            )
        candidate_evaluations.append(
            CandidateEvaluation(
                stone_id=ids[name],
                external_id=f"external-{name}",
                eligible=True,
                reasons=reasons,
                exclusion_rules=[],
                outcome="recommended",
            )
        )

    pair_source_id = pair_document.source_key if pair_document is not None else "unused-pair"
    citations = {
        "card": {
            "stone-a": [f"stone-card:{ids['stone-a']}"],
            "stone-b": [f"stone-card:{ids['stone-b']}"],
        },
        "observations": {name: [f"case-event:{event_ids[name]}"] for name in ids},
        "cross_candidate": {
            "stone-a": [f"stone-card:{ids['stone-a']}"],
            "stone-b": [f"case-event:{event_ids['stone-a']}"],
        },
        "unknown": {
            "stone-a": [f"stone-card:{ids['stone-a']}"],
            "stone-b": ["unknown-source"],
        },
        "mixed_good_bad": {
            "stone-a": [f"stone-card:{ids['stone-a']}", f"case-event:{event_ids['stone-b']}"],
            "stone-b": [f"stone-card:{ids['stone-b']}"],
        },
        "empty": {
            "stone-a": [],
            "stone-b": [f"stone-card:{ids['stone-b']}"],
        },
        "shared_encyclopedia": {
            "stone-a": [shared_id],
            "stone-b": [shared_id],
        },
        "shared_compatibility": {
            "stone-a": [pair_source_id],
            "stone-b": [pair_source_id],
        },
    }[case]
    draft = workflow.AnswerDraft(
        explanations=[
            workflow.CandidateExplanation(
                stone_id=ids[name],
                explanation=f"Generated explanation for {name}.",
                evidence_ids=citations[name],
            )
            for name in ids
        ]
    )
    allowed_in_prompt: dict[str, list[str]] = {}

    class FixtureAnswerModel:
        def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
            def answer(messages: Any) -> dict[str, Any]:
                payload = json.loads(messages[-1].content)
                allowed_in_prompt.update(
                    {
                        stone_id: candidate["allowed_evidence_ids"]
                        for stone_id, candidate in payload["candidates"].items()
                    }
                )
                return {
                    "raw": AIMessage(content="", response_metadata={"finish_reason": "stop"}),
                    "parsed": draft,
                }

            return RunnableLambda(answer)

    state: workflow.SearchState = {
        "question": "Find a calm companion.",
        "messages": [],
        "tools_used": 1,
        "candidate_cards": {ids[name]: {"name": name} for name in ids},
        "verified_statuses": {ids[name]: "AVAILABLE" for name in ids},
        "recommended_stone_ids": [ids["stone-a"], ids["stone-b"]],
        "candidate_evaluations": [item.model_dump(mode="json") for item in candidate_evaluations],
        "evaluation_sources": evaluation_sources,
    }
    result = await workflow.answer(
        state,
        runtime=Runtime(
            context=cast(
                Any,
                SimpleNamespace(
                    tools=SimpleNamespace(
                        details_tool=SimpleNamespace(name="get_stone_details"),
                        compatibility_tool=SimpleNamespace(name="get_compatibility_pair"),
                    ),
                    models=SimpleNamespace(answer_model=FixtureAnswerModel()),
                ),
            )
        ),
    )
    answer_text = cast(dict[str, Any], result["result"])["answer"]
    for name in ids:
        generated = f"Generated explanation for {name}." in answer_text
        assert generated is (name in expected_prose_ids)
    assert all(
        f"stone-card:{stone_id}" in allowed for stone_id, allowed in allowed_in_prompt.items()
    )
    assert f"case-event:{event_ids['stone-a']}" not in allowed_in_prompt[ids["stone-b"]]
    if case == "shared_encyclopedia":
        assert all(shared_id in allowed for allowed in allowed_in_prompt.values())
    if case == "shared_compatibility":
        assert pair_document is not None
        assert all(pair_document.source_key in allowed for allowed in allowed_in_prompt.values())
    fallback_name = {
        "cross_candidate": "stone-b",
        "unknown": "stone-b",
        "mixed_good_bad": "stone-a",
        "empty": "stone-a",
    }.get(case)
    if fallback_name:
        assert f"{fallback_name} observation quote." in answer_text
        sources = cast(dict[str, Any], result["result"])["sources"]
        assert f"case-event:{event_ids[fallback_name]}" in sources
