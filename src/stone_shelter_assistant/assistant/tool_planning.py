"""Typed lookup requests and the model's proposed tool plan."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from stone_shelter_assistant.assistant.candidate_evaluation import SearchCriteria
from stone_shelter_assistant.search.enums import CompatibilityVerdict
from stone_shelter_assistant.stones.enums import StoneType

type PlannedTool = Literal[
    "search_candidates",
    "get_stone_status_by_name",
    "get_stone_details",
    "get_case_timeline",
    "search_knowledge_lexical",
    "get_compatibility_pair",
    "list_compatibility_pairs",
]

type StoneInfoTopic = Literal["overview", "preferences", "care", "history"]


class RequestedPair(BaseModel):
    first_type: StoneType | None
    second_type: StoneType


class RequestedPairList(BaseModel):
    stone_type: StoneType
    verdict: CompatibilityVerdict


class ReferenceRequest(BaseModel):
    stone_name: str | None
    recommendation_name: str | None = None
    care_types: list[StoneType]
    pairs: list[RequestedPair]
    pair_lists: list[RequestedPairList]
    stone_info: StoneInfoTopic | None = None
    unsupported_care: list[str] = Field(default_factory=list)


class ToolPlan(BaseModel):
    """Order the tools needed for the parsed goals and briefly explain the choice."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    tools: list[PlannedTool] = Field(max_length=7)
    reason: str = Field(min_length=1)


def permitted_tools(criteria: SearchCriteria, request: ReferenceRequest) -> list[PlannedTool]:
    """Derive the scope the plan must cover from the parsed request."""
    tools: list[PlannedTool] = ["search_candidates"] if criteria.recommendation_limit else []
    needs_stone = (
        request.stone_info is not None
        or bool(criteria.requested_availability)
        or request.recommendation_name is not None
        or (bool(request.stone_name) and any(pair.first_type is None for pair in request.pairs))
        or (
            not criteria.recommendation_limit
            and any(pair.first_type is None for pair in request.pairs)
        )
    )
    if needs_stone:
        if request.stone_name is None and request.recommendation_name is None:
            if request.stone_info is not None:
                return []
        else:
            tools.append("get_stone_status_by_name")
    if request.stone_info is not None:
        tools.append("get_stone_details")
    if request.stone_info in ("overview", "history"):
        tools.append("get_case_timeline")
    if request.care_types or request.unsupported_care or request.stone_info in ("overview", "care"):
        tools.append("search_knowledge_lexical")
    if request.pairs and any(
        pair.first_type is not None or request.stone_name is not None for pair in request.pairs
    ):
        tools.append("get_compatibility_pair")
    if request.pair_lists or request.stone_info == "overview":
        tools.append("list_compatibility_pairs")
    return tools


def plan_error(plan: ToolPlan, allowed: list[PlannedTool], request: ReferenceRequest) -> str | None:
    """Check coverage and data dependencies before invoking any planned tool."""
    if len(plan.tools) != len(allowed) or set(plan.tools) != set(allowed):
        return "tools_do_not_match_parsed_goals"
    if request.stone_info is not None:
        if "get_stone_details" not in plan.tools:
            return "named_information_not_covered"
        if plan.tools.index("get_stone_status_by_name") > plan.tools.index("get_stone_details"):
            return "stone_name_must_be_resolved_before_card"
        for dependent in (
            "get_case_timeline",
            "search_knowledge_lexical",
            "list_compatibility_pairs",
            "get_compatibility_pair",
        ):
            if dependent in plan.tools and plan.tools.index("get_stone_details") > plan.tools.index(
                dependent
            ):
                return "stone_card_must_be_read_before_type_knowledge"
    if (
        request.stone_name is not None
        and any(pair.first_type is None for pair in request.pairs)
        and "get_compatibility_pair" in plan.tools
    ):
        if plan.tools.index("get_stone_status_by_name") > plan.tools.index(
            "get_compatibility_pair"
        ):
            return "stone_type_must_be_read_before_pair"
    return None
