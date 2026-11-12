"""Execute a validated reference plan without entering candidate search."""

from dataclasses import dataclass, field

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool

from stone_shelter_assistant.assistant.reference_evidence import (
    ReferenceSource,
    case_event_source_data,
    case_event_source_id,
)
from stone_shelter_assistant.assistant.tool_planning import (
    ReferenceRequest,
    RequestedPairList,
    ToolPlan,
)
from stone_shelter_assistant.search.document_models import (
    DEFAULT_LANGUAGE,
    CompatibilityPairSearchDocument,
    CompatibilityTypePortraitSearchDocument,
    EncyclopediaSectionSearchDocument,
)
from stone_shelter_assistant.search.enums import CompatibilityVerdict, DocumentKind
from stone_shelter_assistant.stones.stone_contracts import NamedStoneStatus, StoneDetails


@dataclass(frozen=True)
class ReferenceTools:
    stone_status: BaseTool
    stone_details: BaseTool
    timeline: BaseTool
    encyclopedia: BaseTool
    exact_pair: BaseTool
    pair_list: BaseTool


@dataclass
class ReferenceResult:
    stone: NamedStoneStatus | None = None
    card: StoneDetails | None = None
    lines: list[str] = field(default_factory=list)
    sources: dict[str, dict[str, object]] = field(default_factory=dict)
    context_sources: dict[str, ReferenceSource] = field(default_factory=dict)


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
            case "get_stone_details":
                if result.stone is None:
                    continue
                data = await tools.stone_details.ainvoke(
                    {"stone_id": str(result.stone.stone_id)}, config=config
                )
                if data is None:
                    result.lines.append("The individual stone card is unavailable.")
                    continue
                card = StoneDetails.model_validate(data)
                result.card = card
                result.stone = NamedStoneStatus(
                    stone_id=card.id,
                    name=card.name,
                    stone_type=card.stone_type,
                    adoption_status=card.shelter_case.adoption_status,
                )
                key = f"stone-card:{card.id}"
                result.sources[key] = {
                    "tool": tools.stone_details.name,
                    "data": card.model_dump(mode="json"),
                }
                facts = [f"Biography: {card.biography}"] if card.biography else []
                if card.profile:
                    facts.extend(
                        f"{field}: {value}"
                        for field, value in card.profile.model_dump(mode="json").items()
                        if value
                    )
                if facts:
                    result.context_sources[key] = ReferenceSource(
                        source_id=key, scope="individual", text="\n".join(facts)
                    )
                else:
                    result.lines.append("No individual biography or profile facts are recorded.")
            case "get_case_timeline":
                if result.card is None:
                    continue
                events = await tools.timeline.ainvoke(
                    {"case_external_id": str(result.card.shelter_case.external_id)},
                    config=config,
                )
                unique_events = {
                    event["event_external_id"]: event
                    for event in events
                    if isinstance(event, dict) and isinstance(event.get("event_external_id"), str)
                }
                if not unique_events:
                    result.lines.append("No case observations are recorded.")
                for event_id, event in unique_events.items():
                    source_id = case_event_source_id(event_id)
                    data = case_event_source_data(
                        event,
                        stone_id=str(result.card.id),
                        case_external_id=str(result.card.shelter_case.external_id),
                    )
                    text = data["event_notes"]
                    result.sources[source_id] = {"tool": tools.timeline.name, "data": data}
                    result.context_sources[source_id] = ReferenceSource(
                        source_id=source_id,
                        scope="history",
                        text=text,
                        event_type=data["event_type"],
                        occurred_at=data["occurred_at"],
                        stone_id=data["stone_id"],
                        case_external_id=data["case_external_id"],
                    )
                    result.lines.append(
                        f"**Case event** · {event['occurred_at']} · {event['event_type']} · "
                        f"{source_id}\n{text}"
                    )
            case "search_knowledge_lexical":
                for material in request.unsupported_care:
                    result.lines.append(
                        f"No authored encyclopedia care information is available for {material}."
                    )
                types = list(request.care_types)
                if result.card and request.stone_info in ("overview", "care"):
                    types.append(result.card.stone_type)
                for stone_type in dict.fromkeys(types):
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
                        result.sources[chapter.source_key] = {
                            "tool": tools.encyclopedia.name,
                            "data": chapter.model_dump(mode="json"),
                        }
                        result.context_sources[chapter.source_key] = ReferenceSource(
                            source_id=chapter.source_key, scope="encyclopedia", text=chapter.text
                        )
                if request.stone_info == "overview" and result.card:
                    documents = await tools.encyclopedia.ainvoke(
                        {
                            "filters": {
                                "document_kind": DocumentKind.COMPATIBILITY_TYPE_PORTRAIT,
                                "stone_type": result.card.stone_type,
                                "language": DEFAULT_LANGUAGE,
                            },
                            "limit": 1,
                        },
                        config=config,
                    )
                    if not documents:
                        result.lines.append("No compatibility portrait is available for this type.")
                    for document in documents:
                        portrait = CompatibilityTypePortraitSearchDocument.model_validate(document)
                        result.sources[portrait.source_key] = {
                            "tool": tools.encyclopedia.name,
                            "data": portrait.model_dump(mode="json"),
                        }
                        result.context_sources[portrait.source_key] = ReferenceSource(
                            source_id=portrait.source_key, scope="compatibility", text=portrait.text
                        )
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
                lists = list(request.pair_lists)
                if request.stone_info == "overview" and result.card:
                    lists.extend(
                        RequestedPairList(stone_type=result.card.stone_type, verdict=verdict)
                        for verdict in CompatibilityVerdict
                    )
                for requested_list in lists:
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
                        if request.stone_info == "overview":
                            result.context_sources[entry.source_key] = ReferenceSource(
                                source_id=entry.source_key, scope="compatibility", text=entry.text
                            )
                    summary = ", ".join(sorted(partners)) if partners else "No matching pairs."
                    result.lines.append(
                        f"{requested_list.stone_type.value} · `{requested_list.verdict.value}` · {summary}"
                    )
    if result.stone and (include_status or request.stone_info is not None):
        result.lines.insert(0, f"**{result.stone.name}** · `{result.stone.adoption_status.value}`")
    return result
