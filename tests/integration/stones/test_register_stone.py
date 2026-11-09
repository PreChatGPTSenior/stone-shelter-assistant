"""Exercise HTTP registration and transactional rollback with disposable PostgreSQL."""

import json
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import UUID

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from stone_shelter_assistant.assistant.tools import stone_search_tools
from stone_shelter_assistant.core.unit_of_work import SqlAlchemyUnitOfWork
from stone_shelter_assistant.search.infrastructure.qdrant_collections import (
    OPERATIONAL_COLLECTION as QDRANT_COLLECTION,
)
from stone_shelter_assistant.search.infrastructure.typesense_collections import (
    OPERATIONAL_COLLECTION as TYPESENSE_COLLECTION,
)
from stone_shelter_assistant.search.stones.stone_search_service import StoneSearchService
from stone_shelter_assistant.stones.api_contracts import StoneRegistrationRequest
from stone_shelter_assistant.stones.models import (
    CaseEventModel,
    ShelterCaseModel,
    ShelterModel,
    StoneModel,
    StoneProfileModel,
)
from stone_shelter_assistant.stones.repository import (
    SqlAlchemyShelterCaseRepository,
    SqlAlchemyStoneRepository,
)
from stone_shelter_assistant.stones.service import RegisterStoneService

PROJECT_ROOT = Path(__file__).resolve().parents[3]
TEST_DATA = PROJECT_ROOT / "tests/fixtures/stone-registration"
VALID_REQUESTS = sorted((PROJECT_ROOT / "fixtures/stones").glob("*.json"))
INVALID_REQUESTS = sorted((TEST_DATA / "invalid-persistence").glob("*.json"))
INVALID_VALIDATION_REQUESTS = sorted((TEST_DATA / "invalid-validation").glob("*.json"))
EXPECTED_VALIDATION_ERRORS: dict[str, str] = json.loads(
    (TEST_DATA / "expected-validation-errors.json").read_text()
)
EXPECTED_ERRORS: dict[str, str] = json.loads(
    (TEST_DATA / "expected-persistence-errors.json").read_text()
)


@pytest_asyncio.fixture
async def registration_sessions(
    app: FastAPI,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    sessions: async_sessionmaker[AsyncSession] = app.state.session_factory
    try:
        shelters = json.loads((PROJECT_ROOT / "fixtures/shelters.json").read_text())
        async with sessions() as session, session.begin():
            session.add_all(
                ShelterModel(
                    id=UUID(row["id"]),
                    name=row["name"],
                    address=row["address"],
                )
                for row in shelters
            )
        yield sessions
    finally:
        # Only the disposable Testcontainers database is used by this fixture.
        async with sessions() as session:
            for model in (
                CaseEventModel,
                StoneProfileModel,
                ShelterCaseModel,
                StoneModel,
                ShelterModel,
            ):
                await session.execute(delete(model))
            await session.commit()


async def register(
    sessions: async_sessionmaker[AsyncSession],
    request: StoneRegistrationRequest,
) -> UUID:
    async with SqlAlchemyUnitOfWork(sessions) as uow:
        service = RegisterStoneService(SqlAlchemyStoneRepository(uow.session), uow)
        return await service.register(request)


@pytest.mark.asyncio
@pytest.mark.parametrize("request_file", VALID_REQUESTS, ids=lambda path: path.stem)
async def test_registration_endpoint_persists_complete_graph(
    app: FastAPI,
    registration_sessions: async_sessionmaker[AsyncSession],
    request_file: Path,
) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/stones",
            content=request_file.read_bytes(),
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 201, response.text
    body = response.json()
    assert set(body) == {"id"}
    created_id = UUID(body["id"])
    request = StoneRegistrationRequest.model_validate_json(request_file.read_text())

    # A new session verifies committed rows, not the original identity map.
    async with registration_sessions() as session:
        stone = await session.scalar(
            select(StoneModel)
            .where(StoneModel.id == created_id)
            .options(
                selectinload(StoneModel.profile),
                selectinload(StoneModel.shelter_case).selectinload(ShelterCaseModel.events),
                selectinload(StoneModel.shelter_case).selectinload(
                    ShelterCaseModel.current_shelter
                ),
            )
        )
        assert stone is not None
        assert stone.id.version == 4
        assert stone.external_id == request.stone.external_id
        assert stone.name == request.stone.name
        assert stone.stone_type == request.stone.stone_type.value
        assert stone.stone_size == request.stone.stone_size.value
        assert stone.biography == request.stone.biography
        assert stone.version == 1
        assert stone.created_at.tzinfo is not None

        case = stone.shelter_case
        assert case.stone_id == stone.id
        assert case.external_id == request.shelter_case.external_id
        assert case.case_number == request.shelter_case.case_number
        assert case.current_shelter_id == request.shelter_case.current_shelter_id
        assert case.current_shelter.id == request.shelter_case.current_shelter_id
        assert case.admission_date == request.shelter_case.admission_date
        assert case.adoption_status == request.shelter_case.adoption_status.value
        assert case.version == 1

        expected_events = sorted(request.shelter_case.events, key=lambda event: event.occurred_at)
        assert len(case.events) == len(expected_events)
        for actual, expected in zip(case.events, expected_events, strict=True):
            assert actual.case_id == case.id
            assert actual.external_id == expected.external_id
            assert actual.event_type == expected.event_type.value
            assert actual.occurred_at == expected.occurred_at
            assert actual.event_notes == expected.event_notes
            assert actual.created_at.tzinfo is not None

        if request.profile is None:
            assert stone.profile is None
        else:
            profile = stone.profile
            assert profile is not None
            assert profile.stone_id == stone.id
            assert profile.socialization_traits == sorted(
                trait.value for trait in request.profile.socialization_traits
            )
            assert profile.care_level == (
                request.profile.care_level.value if request.profile.care_level else None
            )
            assert profile.health_notes == request.profile.health_notes
            assert profile.trigger_notes == request.profile.trigger_notes
            assert profile.preferred_environment == request.profile.preferred_environment
            assert profile.version == 1


@pytest.mark.asyncio
async def test_registration_indexes_stone_profile_and_events_in_both_engines(
    app: FastAPI,
    registration_sessions: async_sessionmaker[AsyncSession],
) -> None:
    request_file = PROJECT_ROOT / "fixtures/stones/af5f85d4-9cc7-48a9-a1e6-aad5d8fec581.json"
    request = StoneRegistrationRequest.model_validate_json(request_file.read_text(encoding="utf-8"))

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/stones",
            content=request_file.read_bytes(),
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 201, response.text
    stone_id = UUID(response.json()["id"])

    # A fresh database session verifies that registration committed before indexing.
    async with registration_sessions() as session:
        stone = await session.get(StoneModel, stone_id)
        case = await session.scalar(
            select(ShelterCaseModel).where(ShelterCaseModel.stone_id == stone_id)
        )

    assert stone is not None
    assert stone.external_id == request.stone.external_id
    assert case is not None
    assert case.external_id == request.shelter_case.external_id

    typesense_documents = app.state.typesense_client.collections[TYPESENSE_COLLECTION].documents
    typesense_document = await typesense_documents[str(stone_id)].retrieve()

    assert typesense_document["id"] == str(stone_id)
    assert typesense_document["title"] == request.stone.name
    assert request.stone.biography is not None
    assert request.stone.biography in typesense_document["text"]
    profile = request.profile
    assert profile is not None
    assert profile.care_level is not None
    assert profile.health_notes is not None
    assert profile.trigger_notes is not None
    assert profile.preferred_environment is not None
    assert profile.health_notes in typesense_document["text"]
    assert profile.trigger_notes in typesense_document["text"]
    assert profile.preferred_environment in typesense_document["text"]
    assert typesense_document["care_level"] == profile.care_level.value
    assert set(typesense_document["socialization_traits"]) == {
        trait.value for trait in profile.socialization_traits
    }
    assert typesense_document["stone_type"] == request.stone.stone_type.value
    assert typesense_document["adoption_status"] == request.shelter_case.adoption_status.value
    assert typesense_document["current_shelter_id"] == str(request.shelter_case.current_shelter_id)

    points = await app.state.qdrant_client.retrieve(
        collection_name=QDRANT_COLLECTION,
        ids=[stone_id],
        with_payload=True,
        with_vectors=True,
    )

    assert len(points) == 1
    assert str(points[0].id) == str(stone_id)

    payload = points[0].payload
    assert payload is not None
    assert payload["title"] == typesense_document["title"]
    assert payload["text"] == typesense_document["text"]
    assert payload["stone_type"] == typesense_document["stone_type"]
    assert payload["adoption_status"] == typesense_document["adoption_status"]
    assert payload["current_shelter_id"] == typesense_document["current_shelter_id"]

    vector = points[0].vector
    assert isinstance(vector, list)
    assert len(vector) == app.state.embedding_dimension

    result = await typesense_documents.search(
        {
            "q": "*",
            "query_by": "text",
            "filter_by": (
                f"document_kind:=case_event && case_external_id:={request.shelter_case.external_id}"
            ),
        }
    )
    event_documents = {
        hit["document"]["event_external_id"]: hit["document"] for hit in result["hits"]
    }
    assert result["found"] == len(request.shelter_case.events)
    assert event_documents.keys() == {
        str(event.external_id) for event in request.shelter_case.events
    }

    event_points = await app.state.qdrant_client.retrieve(
        collection_name=QDRANT_COLLECTION,
        ids=[document["id"] for document in event_documents.values()],
        with_payload=True,
        with_vectors=True,
    )
    points_by_id = {str(point.id): point for point in event_points}
    assert points_by_id.keys() == {document["id"] for document in event_documents.values()}

    for event in request.shelter_case.events:
        document = event_documents[str(event.external_id)]
        assert document["text"] == event.event_notes
        assert document["event_type"] == event.event_type.value
        point = points_by_id[document["id"]]
        assert point.payload == {key: value for key, value in document.items() if key != "id"}
        assert isinstance(point.vector, list)
        assert len(point.vector) == app.state.embedding_dimension


@pytest.mark.asyncio
async def test_stone_search_tools_return_registered_card(
    app: FastAPI,
    registration_sessions: async_sessionmaker[AsyncSession],
) -> None:
    fixture = PROJECT_ROOT / "fixtures/stones/67269139-e8b8-4c7d-aa58-33b88162ec70.json"
    request = StoneRegistrationRequest.model_validate_json(fixture.read_text(encoding="utf-8"))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/stones",
            content=fixture.read_bytes(),
            headers={"Content-Type": "application/json"},
        )
    assert response.status_code == 201, response.text
    stone_id = response.json()["id"]

    search = StoneSearchService(
        app.state.typesense_client, app.state.qdrant_client, app.state.embeddings
    )
    async with registration_sessions() as session:
        tools = {
            tool.name: tool
            for tool in stone_search_tools(search, SqlAlchemyShelterCaseRepository(session))
        }
        for name, query in (
            ("search_stones_lexical", request.stone.name),
            ("search_stones_semantic", "a stone that prefers a quiet home"),
        ):
            cards = await tools[name].ainvoke(
                {"query": query, "filters": {"case_number": request.shelter_case.case_number}}
            )
            assert any(
                card["id"] == stone_id and card["document_kind"] == "stone" for card in cards
            )

        states = await tools["get_current_stone_statuses"].ainvoke({"stone_ids": [stone_id]})
        assert states == [
            {
                "stone_id": stone_id,
                "adoption_status": request.shelter_case.adoption_status.value,
                "current_shelter_id": str(request.shelter_case.current_shelter_id),
            }
        ]


@pytest.mark.asyncio
@pytest.mark.parametrize("request_file", INVALID_VALIDATION_REQUESTS, ids=lambda path: path.stem)
async def test_registration_endpoint_rejects_invalid_request(
    app: FastAPI,
    registration_sessions: async_sessionmaker[AsyncSession],
    request_file: Path,
) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/stones",
            content=request_file.read_bytes(),
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 422, response.text
    errors = response.json()["detail"]
    assert len(errors) == 1, errors
    assert errors[0]["loc"][0] == "body"
    assert errors[0]["type"] == EXPECTED_VALIDATION_ERRORS[request_file.name]
    if request_file.name == "too-many-events.json":
        assert errors[0]["ctx"] == {"limit": 100, "actual": 101}
    elif request_file.name == "missing-admission.json":
        assert errors[0]["ctx"] == {"required_event_type": "ADMITTED"}

    async with registration_sessions() as session:
        for model in (StoneModel, StoneProfileModel, ShelterCaseModel, CaseEventModel):
            assert await session.scalar(select(func.count()).select_from(model)) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("request_file", INVALID_REQUESTS, ids=lambda path: path.stem)
async def test_failed_registration_rolls_back_entire_graph(
    registration_sessions: async_sessionmaker[AsyncSession],
    request_file: Path,
) -> None:
    existing_request = StoneRegistrationRequest.model_validate_json(
        (PROJECT_ROOT / "fixtures/stones/49cf225d-800f-4dce-8eb5-af192d2449d5.json").read_text()
    )
    existing_id = await register(registration_sessions, existing_request)
    models = (StoneModel, StoneProfileModel, ShelterCaseModel, CaseEventModel)
    async with registration_sessions() as session:
        before = [await session.scalar(select(func.count()).select_from(model)) for model in models]

    # These requests pass DTO validation and fail only when PostgreSQL writes the graph.
    invalid_request = StoneRegistrationRequest.model_validate_json(request_file.read_text())
    with pytest.raises(IntegrityError) as error:
        await register(registration_sessions, invalid_request)

    assert getattr(error.value.orig, "sqlstate", None) == EXPECTED_ERRORS[request_file.name]
    async with registration_sessions() as session:
        after = [await session.scalar(select(func.count()).select_from(model)) for model in models]
        assert after == before
        assert await session.get(StoneModel, existing_id) is not None
        assert (
            await session.scalar(
                select(StoneModel.id).where(
                    StoneModel.external_id == invalid_request.stone.external_id
                )
            )
            is None
        )
