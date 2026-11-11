"""Execute a validated reference plan without entering candidate search."""

from dataclasses import dataclass, field

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool

from stone_shelter_assistant.assistant.tool_planning import ReferenceRequest, ToolPlan
from stone_shelter_assistant.search.document_models import (
    DEFAULT_LANGUAGE,
    CompatibilityPairSearchDocument,
    EncyclopediaSectionSearchDocument,
)
from stone_shelter_assistant.search.enums import DocumentKind
from stone_shelter_assistant.stones.stone_contracts import NamedStoneStatus


@dataclass(frozen=True)
class ReferenceTools:
    stone_status: BaseTool
    encyclopedia: BaseTool
    exact_pair: BaseTool
    pair_list: BaseTool


@dataclass
class ReferenceResult:
    stone: NamedStoneStatus | None = None
    lines: list[str] = field(default_factory=list)
    sources: dict[str, dict[str, object]] = field(default_factory=dict)
    care_sources: dict[str, dict[str, object]] = field(default_factory=dict)


async def read_reference(
    plan: ToolPlan,
    request: ReferenceRequest,
    tools: ReferenceTools,
    config: RunnableConfig,
    *,
    include_status: bool,
) -> ReferenceResult:
    """Resolve arguments from the parsed question and keep each tool's evidence."""
    result = ReferenceResult()
    for step in plan.tools:
        match step:
            case "get_stone_status_by_name":
                matches = await tools.stone_status.ainvoke(
                    {"name": request.stone_name}, config=config
                )
                if len(matches) == 1:
                    result.stone = NamedStoneStatus.model_validate(matches[0])
                    stone = result.stone
                    if include_status:
                        result.lines.append(f"**{stone.name}** · `{stone.adoption_status.value}`")
                    result.sources[f"stone-status:{stone.stone_id}"] = {
                        "tool": tools.stone_status.name,
                        "data": stone.model_dump(mode="json"),
                    }
                elif matches:
                    result.lines.append(
                        f"Multiple stones are named {request.stone_name}. Please clarify."
                    )
                else:
                    result.lines.append(f"No stone found with the name {request.stone_name}.")
            case "search_knowledge_lexical":
                for stone_type in request.care_types:
                    documents = await tools.encyclopedia.ainvoke(
                        {
                            "filters": {
                                "document_kind": DocumentKind.ENCYCLOPEDIA_SECTION,
                                "stone_type": stone_type,
                                "language": DEFAULT_LANGUAGE,
                            },
                            "limit": 1,
                        },
                        config=config,
                    )
                    if not documents:
                        result.lines.append(f"No encyclopedia entry found for {stone_type.value}.")
                    for document in documents:
                        chapter = EncyclopediaSectionSearchDocument.model_validate(document)
                        result.care_sources[chapter.source_key] = {
                            "tool": tools.encyclopedia.name,
                            "data": chapter.model_dump(mode="json"),
                        }
            case "get_compatibility_pair":
                for requested in request.pairs:
                    first = requested.first_type or (
                        result.stone.stone_type if result.stone else None
                    )
                    if first is None:
                        continue
                    data = await tools.exact_pair.ainvoke(
                        {"first_type": first, "second_type": requested.second_type}, config=config
                    )
                    if data is None:
                        result.lines.append(
                            f"{first.value} + {requested.second_type.value} · `UNKNOWN`"
                        )
                        continue
                    pair = CompatibilityPairSearchDocument.model_validate(data)
                    result.sources[pair.source_key] = {
                        "tool": tools.exact_pair.name,
                        "data": pair.model_dump(mode="json"),
                    }
                    result.lines.append(
                        f"{first.value} + {requested.second_type.value} · `{pair.verdict.value}`"
                    )
            case "list_compatibility_pairs":
                for requested_list in request.pair_lists:
                    documents = await tools.pair_list.ainvoke(
                        {
                            "stone_type": requested_list.stone_type,
                            "verdict": requested_list.verdict,
                        },
                        config=config,
                    )
                    partners = set()
                    for document in documents:
                        entry = CompatibilityPairSearchDocument.model_validate(document)
                        partner = next(
                            (
                                kind
                                for kind in entry.stone_types
                                if kind != requested_list.stone_type
                            ),
                            requested_list.stone_type,
                        )
                        partners.add(partner.value)
                        result.sources[entry.source_key] = {
                            "tool": tools.pair_list.name,
                            "data": entry.model_dump(mode="json"),
                        }
                    summary = ", ".join(sorted(partners)) if partners else "No matching pairs."
                    result.lines.append(
                        f"{requested_list.stone_type.value} · `{requested_list.verdict.value}` · {summary}"
                    )
    result.sources.update(result.care_sources)
    return result
