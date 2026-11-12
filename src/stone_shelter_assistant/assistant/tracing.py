"""Keep Langfuse observations aligned with the workflow stages."""

import json
from hashlib import sha256
from typing import Any
from uuid import UUID

from langchain_core.messages import BaseMessage, ToolMessage
from langfuse import (
    Langfuse,
    LangfuseAgent,
    LangfuseChain,
    LangfuseGeneration,
    LangfuseRetriever,
    LangfuseSpan,
    LangfuseTool,
)
from langfuse.langchain import CallbackHandler
from langfuse.types import TraceContext
from pydantic import BaseModel, ValidationError

TRACE_FIELDS = (
    "grounding_status",
    "question_coverage_status",
    "question_coverage_audit",
    "blocked_tools",
    "grounding_error_type",
    "grounding_catalog",
    "grounding_decisions",
    "retrieval",
    "parser_diagnostics",
    "retrieval_provenance",
    "selection_decisions",
    "selected_stone_ids",
    "verified_statuses",
    "criteria",
    "criteria_status",
    "reference_request",
    "permitted_tools",
    "tool_plan",
    "plan_status",
    "plan_error",
    "selection_status",
    "selection_output_method",
    "assessment_status",
    "assessment_output_method",
    "reference_assessment_status",
    "reference_quote_diagnostics",
    "reference_answer_status",
    "evaluation_policy",
    "tools_used",
    "search_end_reason",
    "stop_reason",
    "duplicate_criteria_removed",
)


def retrieval_trace_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [retrieval_trace_value(item) for item in value]
    return value


def trace_result(result: dict[str, Any], *, include_answer: bool = False) -> dict[str, Any]:
    """Project the final API result into telemetry without copying its source documents."""
    summary: dict[str, Any] = {
        key: result[key]
        for key in (
            "verified_statuses",
            "recommended_stone_ids",
            "candidate_decisions",
            "plan_status",
            "grounding_status",
    "question_coverage_status",
    "question_coverage_audit",
    "blocked_tools",
            "stop_reason",
        )
        if key in result
    }
    summary["source_refs"] = list(result.get("sources", {}))
    if include_answer and "answer" in result:
        summary["answer"] = result["answer"]
    return summary


def trace_state(value: Any, *, output: bool = False) -> dict[str, Any]:
    """Record stage inputs and updates instead of the accumulated LangGraph state."""
    if not isinstance(value, dict):
        return {}
    summary = {key: value[key] for key in TRACE_FIELDS if key in value}
    if "candidate_cards" in value:
        summary["candidate_ids"] = list(value["candidate_cards"])
    if "evaluation_sources" in value:
        summary["source_refs"] = list(value["evaluation_sources"])
    if output and "candidate_evaluations" in value:
        summary["candidate_evaluations"] = value["candidate_evaluations"]
    if output and "result" in value:
        summary["result"] = trace_result(value["result"])
    if output and "reference_result" in value:
        reference = value["reference_result"]
        summary["source_refs"] = list(reference.sources)
    if "reference_quotes" in value:
        summary["reference_quotes"] = [
            quote.model_dump(mode="json") for quote in value["reference_quotes"]
        ]
    return summary


class WorkflowTraceHandler(CallbackHandler):
    """Attach observations nested in LangChain wrappers to the owning workflow stage."""

    def __init__(self, *, public_key: str, trace_context: TraceContext) -> None:
        super().__init__(public_key=public_key, trace_context=trace_context)
        self._hidden_parents: dict[UUID, UUID] = {}
        self._transition_runs: set[UUID] = set()
        self._transitions: dict[UUID, str] = {}
        self._validation_errors: dict[UUID, list[dict[str, Any]]] = {}
        self._source_observations: dict[tuple[str, str], str] = {}
        self._source_text_refs: dict[str, dict[str, str]] = {}
        self._retrieval_runs: set[UUID] = set()

    def on_chain_start(
        self,
        serialized: dict[str, Any] | None,
        inputs: Any,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        name = self.get_langchain_run_name(serialized, **kwargs)
        if name in {"typesense_search", "qdrant_search", "rrf_fusion"}:
            self._retrieval_runs.add(run_id)
        if parent_run_id is not None and (
            name.startswith(("Runnable", "after_"))
            or name in {"PydanticToolsParser", "PydanticOutputParser"}
        ):
            self._hidden_parents[run_id] = self._hidden_parents.get(parent_run_id, parent_run_id)
            if name.startswith("after_"):
                self._transition_runs.add(run_id)
            # Track callback ancestry for metadata propagation without creating a span.
            self._track_run(run_id=run_id, parent_run_id=parent_run_id, metadata=metadata)
            return

        super().on_chain_start(
            serialized,
            retrieval_trace_value(inputs)
            if run_id in self._retrieval_runs
            else trace_state(inputs),
            run_id=run_id,
            parent_run_id=parent_run_id,
            metadata=metadata,
            **kwargs,
        )

    def on_chain_end(
        self, outputs: Any, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any
    ) -> None:
        owner = self._hidden_parents.get(run_id)
        if owner is not None:
            if run_id in self._transition_runs and isinstance(outputs, str):
                self._transitions[owner] = "__end__" if outputs == "done" else outputs
            if isinstance(outputs, dict) and isinstance(
                error := outputs.get("parsing_error"), BaseException
            ):
                self._record_validation_error(owner, error)
            return

        if run_id in self._retrieval_runs:
            observation = self._runs.get(run_id)
            summary = retrieval_trace_value(outputs)
            if observation is not None:
                summary = self._reference_sources(summary, observation.id)
            super().on_chain_end(summary, run_id=run_id, parent_run_id=parent_run_id, **kwargs)
            return

        summary = (
            trace_result(outputs.get("result", {}))
            if parent_run_id is None and isinstance(outputs, dict)
            else trace_state(outputs, output=True)
        )
        if run_id in self._transitions:
            summary["next_stage"] = self._transitions.pop(run_id)
        if run_id in self._validation_errors:
            summary["validation_errors"] = self._validation_errors.pop(run_id)
        # LangChain can also supply the full original state through kwargs.
        if "inputs" in kwargs:
            kwargs["inputs"] = trace_state(kwargs["inputs"])
        super().on_chain_end(summary, run_id=run_id, parent_run_id=parent_run_id, **kwargs)

    def _record_validation_error(self, owner: UUID, error: BaseException) -> None:
        detail: dict[str, Any] = {"type": type(error).__name__}
        if isinstance(error, ValidationError):
            detail["fields"] = [
                {"location": entry["loc"], "type": entry["type"], "message": entry["msg"]}
                for entry in error.errors(include_input=False, include_url=False)
            ]
        else:
            detail["message"] = str(error).split("\n", 1)[0][:300]
        errors = self._validation_errors.setdefault(owner, [])
        if detail not in errors:
            errors.append(detail)

    def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        owner = self._hidden_parents.get(run_id)
        if owner is not None:
            self._record_validation_error(owner, error)
            return
        if "inputs" in kwargs:
            kwargs["inputs"] = trace_state(kwargs["inputs"])
        observation = self._runs.get(run_id)
        if observation is not None and run_id in self._validation_errors:
            observation.update(metadata={"validation_errors": self._validation_errors.pop(run_id)})
        super().on_chain_error(error, run_id=run_id, parent_run_id=parent_run_id, **kwargs)

    def _reference_sources(self, value: Any, observation_id: str) -> Any:
        """Store each retrieved source revision once per request and reference later copies."""
        if isinstance(value, list):
            return [self._reference_sources(item, observation_id) for item in value]
        if not isinstance(value, dict):
            return value
        source_key = value.get("source_key")
        if isinstance(source_key, str) and "text" in value:
            revision = sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()
            key = (source_key, revision)
            if key in self._source_observations:
                return {"source_ref": source_key, "observation_id": self._source_observations[key]}
            self._source_observations[key] = observation_id
            if isinstance(value["text"], str):
                self._source_text_refs.setdefault(
                    value["text"], {"source_ref": source_key, "observation_id": observation_id}
                )
            return value
        return {key: self._reference_sources(item, observation_id) for key, item in value.items()}

    def _reference_model_content(self, value: Any) -> Any:
        """Replace source documents already recorded by tools in the model's trace input."""
        if isinstance(value, str):
            if value in self._source_text_refs:
                return self._source_text_refs[value]
            try:
                decoded = json.loads(value)
            except ValueError:
                return value
            if isinstance(decoded, (dict, list)):
                return json.dumps(self._reference_model_content(decoded), ensure_ascii=False)
            return value
        if isinstance(value, list):
            return [self._reference_model_content(item) for item in value]
        if isinstance(value, dict):
            return {key: self._reference_model_content(item) for key, item in value.items()}
        return value

    def on_chat_model_start(
        self,
        serialized: dict[str, Any] | None,
        messages: list[list[BaseMessage]],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        traced_messages = []
        for batch in messages:
            traced_batch = []
            for message in batch:
                content = self._reference_model_content(message.content)
                if isinstance(content, dict):
                    content = json.dumps(content, ensure_ascii=False)
                traced_batch.append(message.model_copy(update={"content": content}))
            traced_messages.append(traced_batch)
        super().on_chat_model_start(
            serialized, traced_messages, run_id=run_id, parent_run_id=parent_run_id, **kwargs
        )

    def on_tool_end(
        self, output: Any, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any
    ) -> None:
        observation = self._runs.get(run_id)
        if observation is not None:
            content = output.content if isinstance(output, ToolMessage) else output
            if isinstance(content, str):
                try:
                    content = json.loads(content)
                except ValueError:
                    pass
            content = self._reference_sources(content, observation.id)
            if isinstance(output, ToolMessage):
                output = output.model_copy(update={"content": json.dumps(content, default=str)})
            else:
                output = content
        super().on_tool_end(output, run_id=run_id, parent_run_id=parent_run_id, **kwargs)

    def _get_parent_observation(
        self, parent_run_id: UUID | None
    ) -> (
        Langfuse
        | LangfuseAgent
        | LangfuseChain
        | LangfuseGeneration
        | LangfuseRetriever
        | LangfuseSpan
        | LangfuseTool
    ):
        if parent_run_id is not None:
            parent_run_id = self._hidden_parents.get(parent_run_id, parent_run_id)
        return super()._get_parent_observation(parent_run_id)
