import json
from typing import Any, cast

import httpx
import pytest
from langchain_openrouter import ChatOpenRouter
from openrouter import OpenRouter
from pydantic import BaseModel, SecretStr, ValidationError

from stone_shelter_assistant.assistant.candidate_evidence import (
    CandidateEvidence,
    assessment_failure_status,
)
from stone_shelter_assistant.assistant.question_grounding import GroundingResponse
from stone_shelter_assistant.assistant.tracing import provider_error_details
from stone_shelter_assistant.assistant.workflow import structured_model


def _strict_properties(value: Any) -> None:
    if isinstance(value, dict):
        if value.get("type") == "object":
            properties = value.get("properties", {})
            assert set(value.get("required", [])) == set(properties)
            assert value.get("additionalProperties") is False
        for nested in value.values():
            _strict_properties(nested)
    elif isinstance(value, list):
        for nested in value:
            _strict_properties(nested)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("schema", "content"),
    [
        (
            CandidateEvidence,
            '{"character": [{"stone_id": "s1", "source_ref": "biography", '
            '"finding": "confirmed", "quote": "calm", "observation_external_id": null, '
            '"criterion_id": "c1", "fragment_id": 1}], "individual_compatibility": []}',
        ),
        (
            GroundingResponse,
            '{"decisions": [], "question_coverage": '
            '{"status": "complete", "summary": "All requests are represented.", "issues": []}}',
        ),
    ],
)
async def test_strict_wire_schema_is_sent_and_parsed_as_original_dto(
    schema: type[BaseModel], content: str
) -> None:
    requests: list[dict[str, Any]] = []

    async def handle(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": "test-completion",
                "object": "chat.completion",
                "created": 1,
                "model": "test/model",
                "system_fingerprint": None,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )

    transport = httpx.MockTransport(handle)
    http_client = httpx.AsyncClient(transport=transport)
    sdk_client = OpenRouter(
        api_key="offline-test-key", async_client=http_client, retry_config=None
    )
    model = ChatOpenRouter(
        model_name="test/model",
        openrouter_api_key=SecretStr("offline-test-key"),
        client=sdk_client,
    )
    try:
        _, runnable = structured_model(model, schema, use_json_schema=True)
        result = await runnable.ainvoke("Return the empty valid response.")
    finally:
        await http_client.aclose()

    assert isinstance(result, dict)
    assert isinstance(result["parsed"], schema)
    assert result["parsing_error"] is None
    assert len(requests) == 1
    body = requests[0]
    assert body["response_format"]["json_schema"]["strict"] is True
    wire_schema = body["response_format"]["json_schema"]["schema"]
    _strict_properties(wire_schema)
    if schema is CandidateEvidence:
        nested = wire_schema["properties"]["character"]["items"]
        assert "observation_external_id" in nested["required"]
        assert {"type": "null"} in nested["properties"]["observation_external_id"]["anyOf"]
        parsed_evidence = cast(CandidateEvidence, result["parsed"])
        assert parsed_evidence.character[0].observation_external_id is None
    else:
        coverage = wire_schema["properties"]["question_coverage"]["properties"]
        assert "issues" in wire_schema["properties"]["question_coverage"]["required"]
        issue = coverage["issues"]["items"]
        assert issue["discriminator"]["propertyName"] == "kind"
        variants = {
            variant["properties"]["kind"]["const"]: variant for variant in issue["oneOf"]
        }
        assert set(variants) == {"omitted", "misclassified", "uncertain"}
        for variant in variants.values():
            assert set(variant["required"]) == set(variant["properties"])
        assert variants["omitted"]["properties"]["atom_id"]["type"] == "null"
        assert variants["misclassified"]["properties"]["atom_id"]["type"] == "string"
        assert {"type": "null"} in variants["uncertain"]["properties"]["atom_id"]["anyOf"]


@pytest.mark.asyncio
async def test_strict_structured_output_retains_observation_id_validation() -> None:
    async def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "test-completion",
                "object": "chat.completion",
                "created": 1,
                "model": "test/model",
                "system_fingerprint": None,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": (
                                '{"character": [{"stone_id": "s1", "source_ref": '
                                '"observation", "finding": "confirmed", "quote": "exact", '
                                '"observation_external_id": null, "criterion_id": "c1", '
                                '"fragment_id": 1}], "individual_compatibility": []}'
                            ),
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
    sdk_client = OpenRouter(api_key="offline-test-key", async_client=http_client, retry_config=None)
    model = ChatOpenRouter(
        model_name="test/model",
        openrouter_api_key=SecretStr("offline-test-key"),
        client=sdk_client,
    )
    try:
        _, runnable = structured_model(model, CandidateEvidence, use_json_schema=True)
        result = await runnable.ainvoke("Return evidence.")
    finally:
        await http_client.aclose()

    assert isinstance(result, dict)
    assert result["parsed"] is None
    assert isinstance(result["parsing_error"], ValidationError)
    assert assessment_failure_status(result["parsing_error"]) == "invalid_source_ref"


@pytest.mark.asyncio
@pytest.mark.parametrize("content", ["null", "[]", '"scalar"'])
async def test_non_object_json_keeps_pydantic_parsing_error(content: str) -> None:
    async def handle(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "test-completion",
                "object": "chat.completion",
                "created": 1,
                "model": "test/model",
                "system_fingerprint": None,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
    sdk_client = OpenRouter(api_key="offline-test-key", async_client=http_client, retry_config=None)
    model = ChatOpenRouter(
        model_name="test/model",
        openrouter_api_key=SecretStr("offline-test-key"),
        client=sdk_client,
    )
    try:
        _, runnable = structured_model(model, CandidateEvidence, use_json_schema=True)
        result = await runnable.ainvoke("Return a wrong-shaped JSON value.")
    finally:
        await http_client.aclose()
    assert isinstance(result, dict)
    assert result["parsed"] is None
    assert isinstance(result["parsing_error"], ValidationError)


def test_provider_error_projection_is_bounded_and_excludes_credentials() -> None:
    class ProviderError(Exception):
        status_code = 400
        body = {
            "error": {
                "code": "invalid_schema",
                "message": "Bearer abcdefghijklmnop failed",
                "metadata": {
                    "provider_name": "TestProvider",
                    "raw": {"reason": "sk-abcdefghijklmnop", "authorization": "secret"},
                },
            }
        }

    details = provider_error_details(ProviderError("unsafe bearer abc"))
    assert details == {
        "status_code": 400,
        "code": "invalid_schema",
        "message": "[REDACTED] failed",
        "provider_name": "TestProvider",
        "raw": {"reason": "[REDACTED]"},
    }
