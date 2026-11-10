"""Wire request-scoped services and indexers to database sessions."""

from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path
from typing import Annotated

from fastapi import Depends, Request
from langchain_core.tools import BaseTool
from langchain_openrouter import ChatOpenRouter
from langfuse import Langfuse, propagate_attributes
from langfuse.langchain import CallbackHandler
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from stone_shelter_assistant.assistant.api_contracts import QuestionRequest
from stone_shelter_assistant.assistant.tools import (
    case_event_search_tools,
    knowledge_search_tools,
    stone_lookup_tools,
    stone_search_tools,
)
from stone_shelter_assistant.assistant.workflow import run_workflow
from stone_shelter_assistant.core.settings import LangfuseSettings, OpenRouterSettings
from stone_shelter_assistant.core.unit_of_work import SqlAlchemyUnitOfWork
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


def get_question_workflow(
    tools: Annotated[dict[str, BaseTool], Depends(get_search_tools)],
) -> QuestionWorkflow:
    async def ask(payload: QuestionRequest) -> dict[str, object]:
        openrouter = OpenRouterSettings()
        model = ChatOpenRouter(
            model_name=payload.model_id or openrouter.model,
            openrouter_api_key=openrouter.api_key,
            temperature=0,
            max_tokens=3072,
            max_retries=0,
            request_timeout=45_000,
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
        with (
            langfuse.start_as_current_observation(
                name="questions",
                as_type="span",
                input={"question": payload.question, "model_id": model.model},
            ) as root,
            propagate_attributes(user_id="local-test-user", metadata=eval_metadata),
        ):
            callback = CallbackHandler(
                public_key=tracing.public_key,
                trace_context={"trace_id": root.trace_id, "parent_span_id": root.id},
            )
            result = await run_workflow(
                question=payload.question,
                model=model,
                agent_tools=[
                    tools["search_stones_lexical"],
                    tools["search_stones_semantic"],
                    tools["get_compatibility_pair"],
                ],
                details_tool=tools["get_stone_details"],
                status_tool=tools["get_current_stone_statuses"],
                compatibility_tool=tools["get_compatibility_pair"],
                encyclopedia_tool=tools["search_knowledge_lexical"],
                config={"callbacks": [callback], "run_name": "search-workflow"},
            )
            root.update(output=result)
            return {**result, "model_id": model.model, "trace_id": root.trace_id}

    return ask


def get_knowledge_indexer(request: Request) -> KnowledgeIndexer:
    return KnowledgeIndexer(
        project_root=Path.cwd(),
        typesense=request.app.state.typesense_client,
        qdrant=request.app.state.qdrant_client,
        embeddings=request.app.state.embeddings,
        embedding_dimension=request.app.state.embedding_dimension,
    )
