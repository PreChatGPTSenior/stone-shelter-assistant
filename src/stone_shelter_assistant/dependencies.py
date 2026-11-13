"""Wire request-scoped services and indexers to database sessions."""

import hashlib
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from fastapi import Depends, Request
from langchain_core.tools import BaseTool
from langchain_openrouter import ChatOpenRouter
from langfuse import Langfuse, propagate_attributes
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from stone_shelter_assistant.assistant.api_contracts import QuestionRequest
from stone_shelter_assistant.assistant.reference_lookup import ReferenceTools
from stone_shelter_assistant.assistant.tools import (
    case_event_search_tools,
    knowledge_search_tools,
    stone_lookup_tools,
    stone_search_tools,
)
from stone_shelter_assistant.assistant.tracing import WorkflowTraceHandler, trace_result
from stone_shelter_assistant.assistant.workflow import (
    WorkflowModels,
    WorkflowTools,
    run_workflow,
)
from stone_shelter_assistant.core.settings import (
    GroundingSettings,
    LangfuseSettings,
    OpenRouterSettings,
)
from stone_shelter_assistant.core.unit_of_work import SqlAlchemyUnitOfWork
from stone_shelter_assistant.search.knowledge.grounding_concept_store_service import (
    GroundingConceptStoreService,
)
from stone_shelter_assistant.search.knowledge.knowledge_indexer import KnowledgeIndexer
from stone_shelter_assistant.search.knowledge.knowledge_search_service import KnowledgeSearchService
from stone_shelter_assistant.search.stones.case_event_search_service import CaseEventSearchService
from stone_shelter_assistant.search.stones.qdrant_indexer import QdrantStoneIndexer
from stone_shelter_assistant.search.stones.stone_indexing_service import StoneIndexingService
from stone_shelter_assistant.search.stones.stone_search_service import StoneSearchService
from stone_shelter_assistant.search.stones.typesense_indexer import TypesenseStoneIndexer
from stone_shelter_assistant.stones.fixture_loader import StoneFixtureLoader
from stone_shelter_assistant.stones.read_services import StoneReadService
from stone_shelter_assistant.stones.repository import (
    SqlAlchemyShelterCaseRepository,
    SqlAlchemyStoneRepository,
)
from stone_shelter_assistant.stones.service import RegisterStoneService, StoneIngestionService

type QuestionWorkflow = Callable[[QuestionRequest, str, str], Awaitable[dict[str, object]]]


@dataclass(frozen=True, slots=True)
class QuestionModelPlan:
    request_default: str
    selection: str
    parsing: str
    evaluation: str
    answer: str

    def stage_model_ids(self) -> dict[str, str]:
        return {
            "select_candidates": self.selection,
            "parse_question": self.parsing,
            "evaluate_candidates": self.evaluation,
            "answer": self.answer,
            "collect_reference_evidence": self.evaluation,
            "ground_question": self.evaluation,
        }


def _resolve_question_model_plan(
    payload: QuestionRequest,
    settings: OpenRouterSettings,
) -> QuestionModelPlan:
    request_default = payload.model_id or settings.model
    selection = (
        payload.selection_model_id
        or payload.model_id
        or settings.selection_model
        or settings.model
    )
    parsing = (
        payload.parsing_model_id
        or payload.model_id
        or settings.parsing_model
        or selection
    )
    evaluation = (
        payload.evaluation_model_id
        or payload.model_id
        or settings.evaluation_model
    )
    answer = (
        payload.answer_model_id
        or payload.model_id
        or settings.answer_model
        or settings.model
    )
    return QuestionModelPlan(
        request_default=request_default,
        selection=selection,
        parsing=parsing,
        evaluation=evaluation,
        answer=answer,
    )


def _configuration_id(configuration: dict[str, object]) -> str:
    serialized = json.dumps(configuration, sort_keys=True, separators=(",", ":"))
    return "cfg-" + hashlib.sha256(serialized.encode()).hexdigest()[:16]


async def get_register_stone_service(
    request: Request,
) -> AsyncIterator[RegisterStoneService]:
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory

    uow = SqlAlchemyUnitOfWork(session_factory)

    async with uow:
        repository = SqlAlchemyStoneRepository(uow.session)
        service = RegisterStoneService(
            repository=repository,
            uow=uow,
        )

        yield service


async def get_stone_indexing_service(
    request: Request,
) -> AsyncIterator[StoneIndexingService]:
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory

    async with session_factory() as session:
        yield StoneIndexingService(
            stone_repository=SqlAlchemyStoneRepository(session),
            shelter_case_repository=SqlAlchemyShelterCaseRepository(session),
            typesense_indexer=TypesenseStoneIndexer(
                typesense_client=request.app.state.typesense_client,
            ),
            qdrant_indexer=QdrantStoneIndexer(
                qdrant_client=request.app.state.qdrant_client,
                embeddings=request.app.state.embeddings,
                embedding_dimension=request.app.state.embedding_dimension,
            ),
        )


def get_stone_ingestion_service(
    registration: Annotated[RegisterStoneService, Depends(get_register_stone_service)],
    indexer: Annotated[StoneIndexingService, Depends(get_stone_indexing_service)],
) -> StoneIngestionService:
    return StoneIngestionService(registration, indexer)


def get_stone_fixture_loader(
    request: Request,
    ingestion: Annotated[StoneIngestionService, Depends(get_stone_ingestion_service)],
) -> StoneFixtureLoader:
    resources = request.app.state
    return StoneFixtureLoader(
        project_root=Path.cwd(),
        sessions=resources.session_factory,
        typesense=resources.typesense_client,
        qdrant=resources.qdrant_client,
        embedding_dimension=resources.embedding_dimension,
        ingestion=ingestion,
    )


async def get_stone_read_service(request: Request) -> AsyncIterator[StoneReadService]:
    sessions: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with sessions() as session:
        yield StoneReadService(
            stones=SqlAlchemyStoneRepository(session),
            cases=SqlAlchemyShelterCaseRepository(session),
        )


def get_search_tools(
    request: Request,
    stones: Annotated[StoneReadService, Depends(get_stone_read_service)],
) -> dict[str, BaseTool]:
    resources = request.app.state
    search_clients = (
        resources.typesense_client,
        resources.qdrant_client,
        resources.embeddings,
    )
    return {
        tool.name: tool
        for tool in (
            *stone_search_tools(StoneSearchService(*search_clients), stones),
            *stone_lookup_tools(stones),
            *case_event_search_tools(CaseEventSearchService(*search_clients), stones),
            *knowledge_search_tools(KnowledgeSearchService(*search_clients)),
        )
    }


def get_grounding_catalog(request: Request) -> GroundingConceptStoreService:
    settings = GroundingSettings()
    return GroundingConceptStoreService(
        request.app.state.typesense_client,
        language=settings.language,
        version=settings.catalog_version,
    )


def get_question_workflow(
    tools: Annotated[dict[str, BaseTool], Depends(get_search_tools)],
    grounding: Annotated[GroundingConceptStoreService, Depends(get_grounding_catalog)],
) -> QuestionWorkflow:
    async def ask(payload: QuestionRequest, user_id: str, session_id: str) -> dict[str, object]:
        openrouter = OpenRouterSettings()
        model_plan = _resolve_question_model_plan(payload, openrouter)
        model_ids = model_plan.stage_model_ids()
        models = {
            model_id: ChatOpenRouter(
                model_name=model_id,
                openrouter_api_key=openrouter.api_key,
                max_tokens=openrouter.max_tokens,
                max_retries=openrouter.max_retries,
                request_timeout=openrouter.request_timeout,
            )
            for model_id in dict.fromkeys(model_ids.values())
        }
        evaluation_max_tokens = payload.evaluation_max_tokens or openrouter.evaluation_max_tokens
        evaluation_effort = (
            payload.evaluation_reasoning_effort or openrouter.evaluation_reasoning_effort
        )
        configuration_id = _configuration_id(
            {
                "model_ids": model_ids,
                "max_tokens": openrouter.max_tokens,
                "max_retries": openrouter.max_retries,
                "request_timeout": openrouter.request_timeout,
                "evaluation_max_tokens": evaluation_max_tokens,
                "evaluation_request_timeout": openrouter.evaluation_request_timeout,
                "evaluation_reasoning_effort": evaluation_effort,
                "selection_json_schema": model_plan.selection
                in openrouter.selection_json_schema_models,
                "evaluation_json_schema": model_plan.evaluation
                in openrouter.evaluation_json_schema_models,
            }
        )
        evaluation_model = models[model_plan.evaluation].model_copy(
            update={
                "max_tokens": evaluation_max_tokens,
                "request_timeout": openrouter.evaluation_request_timeout,
            }
        )
        tracing = LangfuseSettings()
        langfuse = Langfuse(
            public_key=tracing.public_key,
            secret_key=tracing.secret_key.get_secret_value(),
            base_url=tracing.base_url,
        )
        eval_metadata = payload.model_dump(
            include={
                "comparison_id",
                "run_number",
                "eval_case_id",
                "fixture_version",
                "source_hash",
            },
            exclude_none=True,
        )
        eval_metadata.update(
            run_id=session_id,
            configuration_id=configuration_id,
            selection_model_id=model_ids["select_candidates"],
            parsing_model_id=model_ids["parse_question"],
            evaluation_model_id=model_ids["evaluate_candidates"],
            answer_model_id=model_ids["answer"],
            evaluation_max_tokens=str(evaluation_max_tokens),
            evaluation_reasoning_effort=evaluation_effort,
        )
        with (
            langfuse.start_as_current_observation(
                name="questions",
                as_type="span",
                input={
                    "question": payload.question,
                    "model_id": model_plan.request_default,
                    "model_ids": model_ids,
                    "comparison_id": payload.comparison_id,
                    "run_number": payload.run_number,
                    "run_id": session_id,
                    "configuration_id": configuration_id,
                },
            ) as root,
            propagate_attributes(
                user_id=user_id,
                session_id=session_id,
                metadata=eval_metadata,
            ),
        ):
            callback = WorkflowTraceHandler(
                public_key=tracing.public_key,
                trace_context={"trace_id": root.trace_id, "parent_span_id": root.id},
            )
            workflow_models = WorkflowModels(
                selection_model=models[model_plan.selection],
                selection_uses_json_schema=(
                    model_plan.selection in openrouter.selection_json_schema_models
                ),
                parsing_model=models[model_plan.parsing],
                evaluation_model=evaluation_model,
                evaluation_uses_json_schema=(
                    model_plan.evaluation in openrouter.evaluation_json_schema_models
                ),
                answer_model=models[model_plan.answer],
                evaluation_reasoning={"effort": evaluation_effort},
            )
            reference_tools = ReferenceTools(
                stone_status=tools["get_stone_status_by_name"],
                stone_details=tools["get_stone_details"],
                timeline=tools["get_case_timeline"],
                encyclopedia=tools["search_knowledge_lexical"],
                exact_pair=tools["get_compatibility_pair"],
                pair_list=tools["list_compatibility_pairs"],
            )
            workflow_tools = WorkflowTools(
                retrieval=(
                    tools["search_stones_lexical"],
                    tools["search_stones_semantic"],
                    tools["search_stones_hybrid"],
                    tools["get_compatibility_pair"],
                ),
                details_tool=tools["get_stone_details"],
                status_tool=tools["get_current_stone_statuses"],
                timeline_tool=tools["get_case_timeline"],
                compatibility_tool=tools["get_compatibility_pair"],
                encyclopedia_tool=tools["search_knowledge_lexical"],
                reference_tools=reference_tools,
            )
            result = await run_workflow(
                question=payload.question,
                models=workflow_models,
                tools=workflow_tools,
                grounding_catalog=grounding,
                config={"callbacks": [callback], "run_name": "search-workflow"},
            )
            root.update(output=trace_result(result, include_answer=True))
            return {
                **result,
                "model_id": model_plan.request_default,
                "model_ids": model_ids,
                "evaluation_run": {
                    "comparison_id": payload.comparison_id,
                    "run_number": payload.run_number,
                    "run_id": session_id,
                    "session_id": session_id,
                    "configuration_id": configuration_id,
                    "eval_case_id": payload.eval_case_id,
                    "fixture_version": payload.fixture_version,
                    "source_hash": payload.source_hash,
                },
                "trace_id": root.trace_id,
            }

    return ask


def get_knowledge_indexer(request: Request) -> KnowledgeIndexer:
    return KnowledgeIndexer(
        project_root=Path.cwd(),
        typesense=request.app.state.typesense_client,
        qdrant=request.app.state.qdrant_client,
        embeddings=request.app.state.embeddings,
        embedding_dimension=request.app.state.embedding_dimension,
    )
