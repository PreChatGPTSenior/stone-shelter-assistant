"""Typed lookup requests and the model's proposed tool plan."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from stone_shelter_assistant.assistant.candidate_evaluation import SearchCriteria
from stone_shelter_assistant.search.enums import CompatibilityVerdict
from stone_shelter_assistant.stones.enums import StoneType

type PlannedTool = Literal[
    "search_candidates",
    "get_stone_status_by_name",
    "search_knowledge_lexical",
    "get_compatibility_pair",
    "list_compatibility_pairs",
]


class RequestedPair(BaseModel):
    first_type: StoneType | None
    second_type: StoneType


class RequestedPairList(BaseModel):
    stone_type: StoneType
    verdict: CompatibilityVerdict


class ReferenceRequest(BaseModel):
    stone_name: str | None
    care_types: list[StoneType]
    pairs: list[RequestedPair]
    pair_lists: list[RequestedPairList]


class ToolPlan(BaseModel):
    """Order the tools needed for the parsed goals and briefly explain the choice."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    tools: list[PlannedTool] = Field(max_length=4)
    reason: str = Field(min_length=1)


def permitted_tools(criteria: SearchCriteria, request: ReferenceRequest) -> list[PlannedTool]:
    """Derive the scope the plan must cover from the parsed request."""
    if criteria.recommendation_limit:
        return ["search_candidates"]

    tools: list[PlannedTool] = []
    needs_stone = bool(criteria.requested_availability) or any(
        pair.first_type is None for pair in request.pairs
    )
    if needs_stone:
        if request.stone_name is None:
            return []
        tools.append("get_stone_status_by_name")
    if request.care_types:
        tools.append("search_knowledge_lexical")
    if request.pairs:
        tools.append("get_compatibility_pair")
    if request.pair_lists:
        tools.append("list_compatibility_pairs")
    return tools


def plan_error(plan: ToolPlan, allowed: list[PlannedTool], request: ReferenceRequest) -> str | None:
    """Check coverage and data dependencies before invoking any planned tool."""
    if len(plan.tools) != len(allowed) or set(plan.tools) != set(allowed):
        return "tools_do_not_match_parsed_goals"
    if (
        any(pair.first_type is None for pair in request.pairs)
        and "get_compatibility_pair" in plan.tools
    ):
        if plan.tools.index("get_stone_status_by_name") > plan.tools.index(
            "get_compatibility_pair"
        ):
            return "stone_type_must_be_read_before_pair"
    return None
