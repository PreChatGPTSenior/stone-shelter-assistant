"""Wire request-scoped services and indexers to database sessions."""

from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import datetime
from pathlib import Path
from typing import Annotated
from zoneinfo import ZoneInfo

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
from stone_shelter_assistant.assistant.workflow import run_workflow
from stone_shelter_assistant.core.settings import (
    GroundingSettings,
    LangfuseSettings,
    OpenRouterSettings,
)
from stone_shelter_assistant.core.unit_of_work import SqlAlchemyUnitOfWork
from stone_shelter_assistant.search.knowledge.grounding_catalog import GroundingCatalog
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

type QuestionWorkflow = Callable[[QuestionRequest], Awaitable[dict[str, object]]]


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


def get_grounding_catalog(request: Request) -> GroundingCatalog:
    settings = GroundingSettings()
    return GroundingCatalog(
        request.app.state.typesense_client,
        language=settings.language,
        version=settings.catalog_version,
    )


def get_question_workflow(
    tools: Annotated[dict[str, BaseTool], Depends(get_search_tools)],
    grounding: Annotated[GroundingCatalog, Depends(get_grounding_catalog)],
) -> QuestionWorkflow:
    async def ask(payload: QuestionRequest) -> dict[str, object]:
        openrouter = OpenRouterSettings()
        default_model_id = payload.model_id or openrouter.model
        selection_model_id = (
            payload.selection_model_id
            or payload.model_id
            or openrouter.selection_model
            or openrouter.model
        )
        parsing_model_id = (
            payload.parsing_model_id
            or payload.model_id
            or openrouter.parsing_model
            or selection_model_id
        )
        model_ids = {
            "select_candidates": selection_model_id,
            "parse_question": parsing_model_id,
            "evaluate_candidates": payload.evaluation_model_id
            or payload.model_id
            or openrouter.evaluation_model,
            "answer": payload.answer_model_id
            or payload.model_id
            or openrouter.answer_model
            or openrouter.model,
        }
        model_ids["collect_reference_evidence"] = model_ids["evaluate_candidates"]
        model_ids["ground_question"] = model_ids["evaluate_candidates"]
        models = {
            model_id: ChatOpenRouter(
                model_name=model_id,
                openrouter_api_key=openrouter.api_key,
                max_tokens=3072,
                max_retries=0,
                request_timeout=45_000,
            )
            for model_id in dict.fromkeys(model_ids.values())
        }
        evaluation_max_tokens = payload.evaluation_max_tokens or openrouter.evaluation_max_tokens
        evaluation_effort = (
            payload.evaluation_reasoning_effort or openrouter.evaluation_reasoning_effort
        )
        evaluation_model = models[model_ids["evaluate_candidates"]].model_copy(
            update={
                "max_tokens": evaluation_max_tokens,
                "request_timeout": 180_000,
            }
        )
        tracing = LangfuseSettings()
        langfuse = Langfuse(
            public_key=tracing.public_key,
            secret_key=tracing.secret_key.get_secret_value(),
            base_url=tracing.base_url,
        )
        eval_metadata = payload.model_dump(
            include={"eval_case_id", "fixture_version"}, exclude_none=True
        )
        eval_metadata.update(
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
                    "model_id": default_model_id,
                    "model_ids": model_ids,
                },
            ) as root,
            propagate_attributes(
                user_id="local-test-user",
                session_id=f"{datetime.now(ZoneInfo('Asia/Tbilisi')):%Y-%m-%d}-PY-037",
                metadata=eval_metadata,
            ),
        ):
            callback = WorkflowTraceHandler(
                public_key=tracing.public_key,
                trace_context={"trace_id": root.trace_id, "parent_span_id": root.id},
            )
            result = await run_workflow(
                grounding_catalog=grounding,
                question=payload.question,
                selection_model=models[model_ids["select_candidates"]],
                selection_uses_json_schema=selection_model_id
                in openrouter.selection_json_schema_models,
                parsing_model=models[model_ids["parse_question"]],
                evaluation_model=evaluation_model,
                evaluation_reasoning={"effort": evaluation_effort},
                evaluation_uses_json_schema=model_ids["evaluate_candidates"]
                in openrouter.evaluation_json_schema_models,
                answer_model=models[model_ids["answer"]],
                retrieval_tools=[
                    tools["search_stones_lexical"],
                    tools["search_stones_semantic"],
                    tools["search_stones_hybrid"],
                    tools["get_compatibility_pair"],
                ],
                details_tool=tools["get_stone_details"],
                status_tool=tools["get_current_stone_statuses"],
                timeline_tool=tools["get_case_timeline"],
                compatibility_tool=tools["get_compatibility_pair"],
                encyclopedia_tool=tools["search_knowledge_lexical"],
                reference_tools=ReferenceTools(
                    stone_status=tools["get_stone_status_by_name"],
                    stone_details=tools["get_stone_details"],
                    timeline=tools["get_case_timeline"],
                    encyclopedia=tools["search_knowledge_lexical"],
                    exact_pair=tools["get_compatibility_pair"],
                    pair_list=tools["list_compatibility_pairs"],
                ),
                config={"callbacks": [callback], "run_name": "search-workflow"},
            )
            root.update(output=trace_result(result, include_answer=True))
            return {
                **result,
                "model_id": default_model_id,
                "model_ids": model_ids,
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
