"""Direct workflow evaluation over one disposable environment per module.

Opt in with RUN_FULL_RUN_EVALUATION=1. EVALUATION_CASE_IDS defaults to Q02,Q03,Q04.
EVALUATION_MODEL_CONFIGURATIONS may contain a JSON list of named model configurations;
otherwise Luna 5.6 handles parsing/selection/answers and Terra 5.6 handles grounding
and evidence. EVALUATION_COMPARISON_ID and EVALUATION_RUN_NUMBER label executions.
Outputs: test-evaluation-results/manifest.json and <case>/<run_id>/*.json.
Run this module sequentially; parallel workers must not share its manifest/stores.
No semantic judge, model retries, HTTP requests, or synthetic embeddings are used.
"""

import asyncio
import hashlib
import json
import os
from collections.abc import AsyncIterator, Iterator
from contextlib import AsyncExitStack
from dataclasses import asdict, dataclass, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from typing import Any

import pytest
import pytest_asyncio
from langchain_core.tools import BaseTool
from langchain_ollama import OllamaEmbeddings
from langfuse import Langfuse
from pydantic import BaseModel
from qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from typesense import AsyncClient

import stone_shelter_assistant.assistant.workflow as workflow_module
import stone_shelter_assistant.dependencies as dependencies
from stone_shelter_assistant.assistant.api_contracts import QuestionRequest
from stone_shelter_assistant.assistant.tools import (
    case_event_search_tools,
    knowledge_search_tools,
    stone_lookup_tools,
    stone_search_tools,
)
from stone_shelter_assistant.assistant.tracing import WorkflowTraceHandler, provider_error_details
from stone_shelter_assistant.core.database_factories import (
    create_database_engine,
    create_session_factory,
)
from stone_shelter_assistant.core.settings import (
    DatabaseSettings,
    GroundingSettings,
    LangfuseSettings,
    OllamaEmbeddingSettings,
    OpenRouterSettings,
    QdrantSettings,
    TypesenseSettings,
)
from stone_shelter_assistant.core.unit_of_work import SqlAlchemyUnitOfWork
from stone_shelter_assistant.search.infrastructure.client_factories import (
    create_embeddings,
    create_qdrant_client,
    create_typesense_client,
)
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
from tests.evaluation.support.model_configurations import ModelConfiguration, model_configurations
from tests.evaluation.support.run_identity import (
    EvaluationRunIdentity,
    comparison_id_from_environment,
    first_run_number_from_environment,
)
from tests.evaluation.support.scenario_stages import (
    evaluate_scenario_record,
    failed_evaluation_checks,
)
from tests.integration.conftest import database_settings as database_settings
from tests.integration.conftest import migrated_database as migrated_database
from tests.integration.conftest import postgres_container as postgres_container
from tests.integration.conftest import qdrant_container as qdrant_container
from tests.integration.conftest import qdrant_settings as qdrant_settings
from tests.integration.conftest import typesense_container as typesense_container
from tests.integration.conftest import typesense_settings as typesense_settings

ROOT = Path(__file__).resolve().parents[2]
SUITE = ROOT / "fixtures/agent-eval/questions-challenge-20"
RUNS = ROOT / "test-evaluation-results"
pytestmark = [
    pytest.mark.asyncio(loop_scope="module"),
    pytest.mark.skipif(
        os.getenv("RUN_FULL_RUN_EVALUATION") != "1",
        reason="Explicit full-run paid-model opt-in required",
    ),
]


@dataclass
class FullRunEnvironment:
    sessions: async_sessionmaker[AsyncSession]
    typesense: AsyncClient
    qdrant: AsyncQdrantClient
    embeddings: OllamaEmbeddings
    grounding: GroundingConceptStoreService
    langfuse: Langfuse
    manifest: dict[str, Any]
    comparison_id: str
    openrouter: OpenRouterSettings

    def persist_manifest(self) -> None:
        _write_json(RUNS / "manifest.json", self.manifest)

    def tools(self, stones: StoneReadService) -> dict[str, BaseTool]:
        clients = (self.typesense, self.qdrant, self.embeddings)
        return {
            tool.name: tool
            for tool in (
                *stone_search_tools(StoneSearchService(*clients), stones),
                *stone_lookup_tools(stones),
                *case_event_search_tools(CaseEventSearchService(*clients), stones),
                *knowledge_search_tools(KnowledgeSearchService(*clients)),
            )
        }


@dataclass
class FullRun:
    identity: EvaluationRunIdentity
    configuration: ModelConfiguration
    entry: dict[str, Any]


@dataclass
class GraphCapture:
    graph: Any
    states: list[dict[str, Any]]

    async def ainvoke(self, *args: Any, **kwargs: Any) -> Any:
        state = await self.graph.ainvoke(*args, **kwargs)
        self.states.append(_json_value(state))
        return state


def _json_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if is_dataclass(value) and not isinstance(value, type):
        return _json_value(asdict(value))
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(_json_value(value), ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def _cases() -> list[dict[str, Any]]:
    cases = json.loads((SUITE / "scenarios.json").read_text())["scenarios"]
    ids = os.getenv("EVALUATION_CASE_IDS", "Q02,Q03,Q04").split(",")
    ids = [value.strip() for value in ids]
    available = {case["id"]: case for case in cases}
    if not ids or len(ids) != len(set(ids)) or any(value not in available for value in ids):
        raise ValueError("EVALUATION_CASE_IDS must contain unique existing scenario IDs")
    return [available[value] for value in ids]


def _hashes(paths: list[Path]) -> dict[str, str]:
    return {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(set(paths))
    }


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def full_run_environment(
    migrated_database: DatabaseSettings,
    typesense_settings: TypesenseSettings,
    qdrant_settings: QdrantSettings,
) -> AsyncIterator[FullRunEnvironment]:
    """Existing session-scoped Testcontainers supply only disposable connections."""
    if os.getenv("PYTEST_XDIST_WORKER"):
        raise ValueError("Run this suite sequentially, without pytest-xdist workers")
    started = datetime.now(UTC)
    comparison_id = comparison_id_from_environment(started)
    first_run = first_run_number_from_environment()
    manifest_path = RUNS / "manifest.json"
    manifest: dict[str, Any] = (
        json.loads(manifest_path.read_text())
        if manifest_path.exists()
        else {
            "format": "full-run-evaluation-v1",
            "runs": {},
        }
    )
    if manifest.get("format") != "full-run-evaluation-v1":
        raise ValueError("Unexpected full-run manifest format")
    cases = _cases()
    configurations = model_configurations()
    fixture_hashes = _hashes(
        [
            *[
                path
                for path in (ROOT / "fixtures").rglob("*")
                if path.is_file() and path.suffix in {".json", ".md"} and path.name != "README.md"
            ],
            SUITE / "scenarios.json",
            SUITE / "scenario-evaluation-targets.json",
        ]
    )
    code_hashes = _hashes(
        [
            *list((ROOT / "src").rglob("*.py")),
            Path(__file__).resolve(),
            ROOT / "tests/integration/conftest.py",
            ROOT / "tests/evaluation/support/run_identity.py",
            ROOT / "tests/evaluation/support/model_configurations.py",
            ROOT / "tests/evaluation/support/scenario_stages.py",
            ROOT / "tests/evaluation/test_saved_run_evaluation.py",
        ]
    )
    source_hash = hashlib.sha256(json.dumps(code_hashes, sort_keys=True).encode()).hexdigest()
    for index in range(len(configurations)):
        identity = EvaluationRunIdentity.create(comparison_id, first_run + index)
        if identity.run_id in manifest["runs"] or any(
            (RUNS / case["id"] / identity.run_id).exists() for case in cases
        ):
            raise ValueError(f"Run already exists: {identity.run_id}; choose a new run number")
    for index, configuration in enumerate(configurations):
        identity = EvaluationRunIdentity.create(comparison_id, first_run + index)
        manifest["runs"][identity.run_id] = {
            **identity.as_metadata(),
            "session_id": identity.session_id,
            "configuration": configuration.model_dump(),
            "status": "preparing",
            "started_at": started.isoformat(),
            "source_hash": source_hash,
            "source_hashes": code_hashes,
            "fixture_hashes": fixture_hashes,
            "semantic_judge": "disabled",
            "model_retries": 0,
            "cases": {case["id"]: {"status": "not_run"} for case in cases},
        }
    _write_json(manifest_path, manifest)
    try:
        async with AsyncExitStack() as resources:
            engine = create_database_engine(migrated_database)
            resources.push_async_callback(engine.dispose)
            sessions = create_session_factory(engine)
            typesense = create_typesense_client(typesense_settings)
            resources.push_async_callback(typesense.api_call.aclose)
            qdrant = create_qdrant_client(qdrant_settings)
            resources.push_async_callback(qdrant.close)
            embedding_settings = OllamaEmbeddingSettings()
            embeddings = create_embeddings(embedding_settings)
            vector = await embeddings.aembed_query("full-run embedding dimension check")
            if len(vector) != embedding_settings.embedding_dimension:
                raise ValueError("Local Ollama embedding dimension does not match configuration")
            async with SqlAlchemyUnitOfWork(sessions) as uow, sessions() as indexing_session:
                indexer = StoneIndexingService(
                    SqlAlchemyStoneRepository(indexing_session),
                    SqlAlchemyShelterCaseRepository(indexing_session),
                    TypesenseStoneIndexer(typesense),
                    QdrantStoneIndexer(qdrant, embeddings, embedding_settings.embedding_dimension),
                )
                ingestion = StoneIngestionService(
                    RegisterStoneService(SqlAlchemyStoneRepository(uow.session), uow), indexer
                )
                loader = StoneFixtureLoader(
                    ROOT,
                    sessions,
                    typesense,
                    qdrant,
                    embedding_settings.embedding_dimension,
                    ingestion,
                )
                loaded_stones = await loader.reload()
            knowledge = KnowledgeIndexer(
                ROOT, typesense, qdrant, embeddings, embedding_settings.embedding_dimension
            )
            loaded_encyclopedia = await knowledge.reload_encyclopedia()
            loaded_compatibility = await knowledge.reload_compatibility()
            grounding_settings = GroundingSettings()
            grounding = GroundingConceptStoreService(
                typesense,
                language=grounding_settings.language,
                version=grounding_settings.catalog_version,
            )
            snapshot = await grounding.reload(
                ROOT / "fixtures/knowledge/grounding" / f"grounding_{grounding.version}.json"
            )
            tracing = LangfuseSettings()
            client = Langfuse(
                public_key=tracing.public_key,
                secret_key=tracing.secret_key.get_secret_value(),
                base_url=tracing.base_url,
            )
            for index in range(len(configurations)):
                run_id = EvaluationRunIdentity.create(comparison_id, first_run + index).run_id
                manifest["runs"][run_id].update(
                    status="ready",
                    embedding_model=embedding_settings.embedding_model,
                    embedding_dimension=embedding_settings.embedding_dimension,
                    preparation={
                        "stones": loaded_stones,
                        "encyclopedia": loaded_encyclopedia,
                        "compatibility": loaded_compatibility,
                        "grounding_hash": snapshot.content_hash,
                    },
                )
            environment = FullRunEnvironment(
                sessions,
                typesense,
                qdrant,
                embeddings,
                grounding,
                client,
                manifest,
                comparison_id,
                OpenRouterSettings(),
            )
            environment.persist_manifest()
            try:
                yield environment
            finally:
                try:
                    await asyncio.to_thread(client.flush)
                except Exception as error:
                    for index in range(len(configurations)):
                        run_id = EvaluationRunIdentity.create(
                            comparison_id, first_run + index
                        ).run_id
                        manifest["runs"][run_id]["telemetry_flush_error"] = type(error).__name__
                    environment.persist_manifest()
    except Exception as error:
        for index in range(len(configurations)):
            run_id = EvaluationRunIdentity.create(comparison_id, first_run + index).run_id
            if manifest["runs"][run_id]["status"] == "preparing":
                manifest["runs"][run_id].update(
                    status="setup_failed", error_type=type(error).__name__
                )
        _write_json(manifest_path, manifest)
        raise


@pytest.fixture(scope="module", params=model_configurations(), ids=lambda item: item.name)
def full_run(
    request: pytest.FixtureRequest, full_run_environment: FullRunEnvironment
) -> Iterator[FullRun]:
    configuration: ModelConfiguration = request.param
    index = next(
        i for i, item in enumerate(model_configurations()) if item.name == configuration.name
    )
    identity = EvaluationRunIdentity.create(
        full_run_environment.comparison_id, first_run_number_from_environment() + index
    )
    entry = full_run_environment.manifest["runs"][identity.run_id]
    yield FullRun(identity, configuration, entry)
    if entry["status"] in {"ready", "running"}:
        entry.update(status="partial", completed_at=datetime.now(UTC).isoformat())
        full_run_environment.persist_manifest()


async def _capture_observations(client: Langfuse, trace_id: str | None) -> dict[str, Any]:
    result: dict[str, Any] = {"trace_id": trace_id, "status": "not_available", "observations": []}
    if trace_id is None:
        return result
    try:
        await asyncio.to_thread(client.flush)
        for attempt in range(3):
            observations: list[dict[str, Any]] = []
            cursor = None
            while True:
                page = await asyncio.to_thread(
                    client.api.observations.get_many,
                    trace_id=trace_id,
                    limit=1000,
                    fields="basic,io,model,usage",
                    cursor=cursor,
                )
                observations.extend(item.model_dump(mode="json") for item in page.data)
                cursor = page.meta.cursor
                if not cursor:
                    break
            result.update(
                observations=observations, status="retrieved" if observations else "pending"
            )
            if observations or attempt == 2:
                break
            await asyncio.sleep(1)
    except Exception as error:
        result.update(status="capture_failed", error_type=type(error).__name__)
    return result


@pytest.mark.parametrize("case", _cases(), ids=lambda case: case["id"])
async def test_full_run_evaluation(
    full_run_environment: FullRunEnvironment,
    full_run: FullRun,
    case: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Archive actual output before checking execution integrity; no semantic pass claim."""
    environment = full_run_environment
    identity = full_run.identity
    configuration = full_run.configuration
    folder = RUNS / case["id"] / identity.run_id
    folder.mkdir(parents=True, exist_ok=False)
    payload = QuestionRequest(
        question=case["question"],
        model_id=configuration.model_id,
        parsing_model_id=configuration.model_id,
        selection_model_id=configuration.model_id,
        answer_model_id=configuration.model_id,
        evaluation_model_id=configuration.evaluation_model_id,
        evaluation_max_tokens=configuration.max_tokens,
        evaluation_reasoning_effort=configuration.reasoning_effort,
        eval_case_id=case["id"],
        fixture_version=json.loads((SUITE / "scenarios.json").read_text())["suite_id"],
        comparison_id=identity.comparison_id,
        run_number=identity.run_number,
        source_hash=full_run.entry["source_hash"],
    )
    settings = environment.openrouter.model_copy(
        update={
            "max_retries": 0,
            "max_tokens": configuration.max_tokens,
            "request_timeout": 180_000,
            "evaluation_request_timeout": 180_000,
        }
    )
    monkeypatch.setattr(dependencies, "OpenRouterSettings", lambda: settings)
    states: list[dict[str, Any]] = []
    build_graph = workflow_module.build_graph
    monkeypatch.setattr(workflow_module, "build_graph", lambda: GraphCapture(build_graph(), states))
    record: dict[str, Any] = {
        "case_id": case["id"],
        **identity.as_metadata(),
        "session_id": identity.session_id,
        "request": payload.model_dump(mode="json"),
        "question": case["question"],
        "expected": case["expected"],
        "status": "running",
        "trace_id": None,
        "started_at": datetime.now(UTC).isoformat(),
    }

    def callback(**kwargs: Any) -> WorkflowTraceHandler:
        record["trace_id"] = kwargs["trace_context"]["trace_id"]
        return WorkflowTraceHandler(**kwargs)

    monkeypatch.setattr(dependencies, "WorkflowTraceHandler", callback)
    full_run.entry["effective_settings"] = {
        "max_tokens": settings.max_tokens,
        "model_retries": settings.max_retries,
        "request_timeout": settings.request_timeout,
        "evaluation_request_timeout": settings.evaluation_request_timeout,
        "evaluation_reasoning_effort": payload.evaluation_reasoning_effort,
        "selection_json_schema": configuration.model_id in settings.selection_json_schema_models,
        "evaluation_json_schema": configuration.evaluation_model_id
        in settings.evaluation_json_schema_models,
    }
    full_run.entry["status"] = "running"
    full_run.entry["cases"][case["id"]] = {
        "status": "running",
        "result": (folder / "result.json").relative_to(RUNS).as_posix(),
        "observations": (folder / "observations.json").relative_to(RUNS).as_posix(),
    }
    _write_json(folder / "result.json", record)
    environment.persist_manifest()
    started = monotonic()
    try:
        async with environment.sessions() as session:
            stones = StoneReadService(
                SqlAlchemyStoneRepository(session), SqlAlchemyShelterCaseRepository(session)
            )
            ask = dependencies.get_question_workflow(
                environment.tools(stones), environment.grounding
            )
            response = await ask(payload, "STPY-local-test-user", identity.session_id)
            record.update(response=response, trace_id=response.get("trace_id"), status="completed")
            evaluation_run = response.get("evaluation_run")
            if isinstance(evaluation_run, dict):
                full_run.entry["configuration_id"] = evaluation_run.get("configuration_id")
    except Exception as error:
        record.update(
            status="execution_failed",
            technical_error=type(error).__name__,
            provider_error=provider_error_details(error),
        )
    finally:
        if record["status"] == "running":
            record["status"] = "interrupted"
        record.update(
            elapsed_seconds=round(monotonic() - started, 3),
            graph_state=states[-1] if states else None,
        )
        _write_json(folder / "result.json", record)
        telemetry = await _capture_observations(environment.langfuse, record["trace_id"])
        _write_json(folder / "observations.json", telemetry)
        targets = json.loads((SUITE / "scenario-evaluation-targets.json").read_text())["scenarios"]
        report = evaluate_scenario_record(record, targets[case["id"]])
        failures = failed_evaluation_checks({"scenario_reports": [report]})
        record.update(
            stage_evaluation=report,
            failed_checks=failures,
            evaluation_status="pass" if not failures else "fail",
            telemetry_status=telemetry["status"],
            completed_at=datetime.now(UTC).isoformat(),
        )
        _write_json(folder / "result.json", record)
        full_run.entry["cases"][case["id"]].update(
            status=record["status"],
            trace_id=record["trace_id"],
            workflow_integrity=report["workflow_integrity"]["status"],
            evaluation_status=record["evaluation_status"],
            telemetry_status=telemetry["status"],
        )
        statuses = [item["status"] for item in full_run.entry["cases"].values()]
        if all(value not in {"not_run", "running"} for value in statuses):
            full_run.entry.update(
                status="completed" if all(value == "completed" for value in statuses) else "failed",
                completed_at=datetime.now(UTC).isoformat(),
            )
        environment.persist_manifest()
    assert record["status"] == "completed", f"Execution failed; inspect {folder / 'result.json'}"
    assert report["workflow_integrity"]["status"] == "pass", (
        f"Workflow failed; inspect {folder / 'result.json'}"
    )
    assert not failures, f"Reviewed checks failed: {failures}; inspect {folder / 'result.json'}"
