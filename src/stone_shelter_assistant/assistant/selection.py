"""Define structured selection and parsing responses for the search workflow."""

import re
from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool

from stone_shelter_assistant.assistant.candidate_evaluation import (
    CompatibilityCriterion,
    CriteriaGroup,
    HouseholdFact,
    QuotedCriterion,
    SearchCriteria,
)
from stone_shelter_assistant.assistant.question_grounding import GroundingProposal
from stone_shelter_assistant.assistant.ranking_policy import RANKING_POLICY
from stone_shelter_assistant.assistant.tool_planning import (
    ReferenceRequest,
    RequestedPair,
    RequestedPairList,
    StoneInfoTopic,
)
from stone_shelter_assistant.search.document_models import DEFAULT_LANGUAGE
from stone_shelter_assistant.search.enums import AccommodationFactType, CompatibilityVerdict
from stone_shelter_assistant.search.stones.search_contracts import StoneSearchFilters
from stone_shelter_assistant.stones.enums import AdoptionStatus, StoneType


class FragmentReference(BaseModel):
    fragment_id: int = Field(
        ge=1,
        description="One-based ID of the verbatim original question fragment containing this reference.",
    )


class HouseholdFactReference(FragmentReference):
    question_quote: str = Field(
        min_length=1,
        description=(
            "Exact source subquote for the household reference. It may describe context that "
            "explains a criterion; a context quote does not assert an additional typed fact."
        ),
    )
    existing_stone_type: StoneType | None = Field(
        default=None,
        description=(
            "A stone type explicitly said to already live in the household. This is household "
            "context that can trigger pair assessment; its presence alone is not a compatibility "
            "requirement or preference."
        ),
    )
    fact_type: AccommodationFactType | None = Field(
        default=None,
        description=(
            "One currently supported typed household agreement. Other contextual facts have no "
            "fact_type in this contract."
        ),
    )
    value: StrictBool | None = Field(
        default=None,
        description=(
            "Whether the supported agreement was explicitly established for the stated scope. Use "
            "false only for an explicit refusal or denial about that same household or pair. A "
            "positive agreement scoped to another pair, or a statement that it does not apply here, "
            "does not establish false for this pair; leave that pair unrepresented and unknown."
        ),
    )
    applies_to_pair: tuple[StoneType, StoneType] | None = Field(
        default=None,
        description=(
            "The exact type pair to which this explicitly stated agreement or denial applies. "
            "Keep a positive agreement attached to its stated pair; do not create false facts for "
            "pairs it does not cover."
        ),
    )


class CompatibilityReference(FragmentReference):
    household_type: StoneType = Field(
        description=(
            "The explicitly referenced existing or comparison type. This is never the type of a "
            "new recommended stone; put that type in retrieval.candidate_type."
        )
    )
    first_type: StoneType | None = Field(
        default=None,
        description="The other explicit type for a type-to-type compatibility question, if present.",
    )


class CriterionReference(FragmentReference):
    question_quote: str = Field(
        min_length=1,
        description=(
            "Exact source subquote for one decision-bearing character or environmental-fit criterion. "
            "A request for a stone for a stated home describes suitability to that environment; it "
            "does not assert that the stone intrinsically has the home's quality. Include source "
            "context when it explains the criterion; independent criteria get separate entries."
        ),
    )


class CompatibilityCriterionReference(FragmentReference):
    target_type: StoneType = Field(
        description=(
            "Other material type that the new candidate is explicitly required or preferred to live "
            "with. It may be an existing, named, or hypothetical comparison type; this field does "
            "not assert household presence. The same material may also be the candidate type when "
            "the question explicitly requests that same-type pair."
        )
    )
    question_quote: str = Field(
        min_length=1,
        description=(
            "Exact source subquote for one independent compatibility requirement or preference. The "
            "new candidate must be explicitly required or preferred to be compatible with target_type. "
            "Household presence or 'for/with my type' context alone can trigger a pair assessment but "
            "does not create a mandatory compatibility criterion. The type of the new candidate is "
            "a separate role in retrieval.candidate_type; both roles may use the same type only when "
            "both are explicitly requested."
        ),
    )


class RequestedCompatibilityReference(CompatibilityReference):
    target: Literal["candidate", "named_stone", "types"] = Field(
        description=(
            "Whether the original compatibility question concerns a recommended candidate, a "
            "named individual, or two explicit types. Its original fragment carries the full "
            "question, including explanatory or sufficiency wording."
        )
    )


class NamedStoneReference(FragmentReference):
    name: str = Field(min_length=1, description="Exact individual name explicitly referenced in the question.")


class CareReference(FragmentReference):
    stone_type: StoneType = Field(description="Stone type for which the user explicitly requests care advice.")


class UnsupportedCareReference(FragmentReference):
    material: str = Field(
        min_length=1,
        max_length=120,
        description="Exact unsupported material named in an explicit care-advice request.",
    )


class StoneInfoReference(FragmentReference):
    topic: StoneInfoTopic = Field(description="Requested topic about the named individual.")


class PairListReference(FragmentReference):
    stone_type: StoneType = Field(description="Type whose compatibility partners are requested.")
    verdict: CompatibilityVerdict = Field(description="Requested authored compatibility verdict.")


class CriteriaReferences(BaseModel):
    character: list[CriterionReference] = Field(
        default_factory=list,
        description=(
            "Independent required or preferred traits or environmental fit of a recommended stone. "
            "A phrase such as 'for a quiet home' requests suitability to that home without asserting "
            "an intrinsic quiet trait. Source context that explains a criterion may stay in its quote "
            "rather than become a second household fact."
        ),
    )
    compatibility: list[CompatibilityCriterionReference] = Field(
        default_factory=list,
        description="Independent required or preferred compatibility targets for a recommended stone.",
    )

    def resolve(self, fragments: Mapping[int, str], *, group_id: str) -> CriteriaGroup:
        for character_ref in self.character:
            if character_ref.fragment_id not in fragments or character_ref.question_quote not in fragments[character_ref.fragment_id]:
                raise ValueError("Criterion quote must be a source-bound original subquote")
        for compatibility_ref in self.compatibility:
            if compatibility_ref.fragment_id not in fragments or compatibility_ref.question_quote not in fragments[compatibility_ref.fragment_id]:
                raise ValueError("Criterion quote must be a source-bound original subquote")
        return CriteriaGroup(
            character=[
                QuotedCriterion(
                    criterion_id=f"{group_id}.character.{index}",
                    fragment_id=item.fragment_id,
                    question_quote=item.question_quote,
                )
                for index, item in enumerate(self.character, start=1)
            ],
            compatibility=[
                CompatibilityCriterion(
                    criterion_id=f"{group_id}.compatibility.{index}",
                    fragment_id=item.fragment_id,
                    question_quote=item.question_quote,
                    household_type=item.target_type,
                )
                for index, item in enumerate(self.compatibility, start=1)
            ],
        )


class RetrievalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    lexical_query: str = Field(min_length=1)
    semantic_query: str = Field(min_length=1)
    filters: StoneSearchFilters


class CandidateTypeReference(FragmentReference):
    stone_type: StoneType = Field(
        description=(
            "Explicit required material type of the new recommended candidate. A positive type "
            "directly modifying the requested stone noun (for example, 'find a granite stone') is "
            "required without a modal word such as 'must'. An optional or preferred type, or a "
            "negated type, is not a required candidate type. A type modifying an existing household "
            "stone is not a candidate type."
        )
    )


class RetrievalProposal(BaseModel):
    """Queries guide retrieval; they do not add decision criteria or assert evidence."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    lexical_query: str = Field(
        min_length=1,
        description="English lexical search terms; query wording is not a substitute for parsed criteria.",
    )
    semantic_query: str = Field(
        min_length=1,
        description="English semantic retrieval description; it does not create a requirement or preference.",
    )
    candidate_type: CandidateTypeReference | None = Field(
        default=None,
        description=(
            "Only the explicitly required material of the new recommended stone. Extract a positive "
            "type modifying its noun even without 'must'; do not filter on an optional/preferred or "
            "negated type, or on a household stone's type from 'with/for my granite'."
        ),
    )


class ParseQuestion(BaseModel):
    """Classify original-question requests and criteria without candidate data."""

    recommendation_limit: int = Field(
        ge=0,
        description=(
            "Generic recommendation action and requested quantity: positive means recommend that "
            "many stones; zero means no recommendation. A request to explain why a recommended stone "
            "fits is answered from its criteria and evidence; it is not a separate coverage atom. "
            "recommendation_target is only needed when the user explicitly names the candidate."
        ),
    )
    requested_availability: list[FragmentReference] = Field(
        default_factory=list,
        description=(
            "A direct current-status lookup for a referenced individual or explicitly named "
            "candidate when status is an independent goal. Recommendations already use AVAILABLE "
            "retrieval and PostgreSQL status verification, so do not duplicate that built-in "
            "availability behavior here."
        ),
    )
    requested_compatibility: list[RequestedCompatibilityReference] = Field(
        default_factory=list,
        description=(
            "Explicit compatibility questions. The referenced original fragment includes the full "
            "request, including explanation, grounds, or whether a behavior is sufficient; do not "
            "require a separate atom for those words."
        ),
    )
    household_facts: list[HouseholdFactReference] = Field(
        default_factory=list,
        description=(
            "Existing household stone types and currently supported typed agreements. A source-bound "
            "entry with null typed values may carry relevant context for a criterion; do not demand "
            "a new fact enum for context or background."
        ),
    )
    requirements: CriteriaReferences = Field(
        default_factory=CriteriaReferences,
        description=(
            "Explicit required traits, environmental fit, and compatibility criteria for a recommended "
            "stone. For compatibility, a cohabitation constraint must be independently stated; a "
            "household type alone is context. Context may explain a criterion without being a second "
            "criterion. If the exact same source atom is also listed as a preference, the resolver "
            "retains the requirement; distinct source atoms stay separate."
        ),
    )
    preferences: CriteriaReferences = Field(
        default_factory=CriteriaReferences,
        description=(
            "Preferred traits and compatibility targets. Exact same-source overlap with a requirement "
            "uses requirement precedence; do not merge different criteria merely because they share a fragment."
        ),
    )
    named_stone: NamedStoneReference | None = Field(
        default=None,
        description="An individual named for information or reference lookup; not a candidate filter.",
    )
    recommendation_target: NamedStoneReference | None = Field(
        default=None,
        description=(
            "Optional named candidate, only when the user explicitly names which individual to recommend. "
            "A generic recommendation is already represented by recommendation_limit."
        ),
    )
    requested_care: list[CareReference] = Field(
        default_factory=list,
        description="Explicit care-advice requests for supported stone types.",
    )
    unsupported_care: list[UnsupportedCareReference] = Field(
        default_factory=list,
        description="Explicit care-advice requests for materials outside the supported type catalog.",
    )
    requested_stone_info: StoneInfoReference | None = Field(
        default=None,
        description="Requested topic about the individual named in named_stone.",
    )
    requested_pair_lists: list[PairListReference] = Field(
        default_factory=list,
        description="Explicit request for authored compatibility partners of a stone type.",
    )
    retrieval: RetrievalProposal | None = Field(
        default=None,
        description="Search-query preparation for a recommendation; not an independent decision criterion.",
    )

    def resolve_retrieval(
        self, fragments: Mapping[int, str], supported: frozenset[str] = frozenset()
    ) -> RetrievalRequest | None:
        if self.retrieval is None:
            return None
        proposal = self.retrieval
        stone_type = None
        if proposal.candidate_type is not None:
            candidate = proposal.candidate_type
            if "candidate_type" in supported:
                stone_type = candidate.stone_type
        return RetrievalRequest(
            lexical_query=proposal.lexical_query,
            semantic_query=proposal.semantic_query,
            filters=StoneSearchFilters(
                adoption_status=AdoptionStatus.AVAILABLE,
                language=DEFAULT_LANGUAGE,
                stone_type=stone_type,
            ),
        )

    def parsed_atoms(self, fragments: Mapping[int, str]) -> list[dict[str, object]]:
        """Expose the complete typed parse as source-bound atoms for a coverage audit."""
        atoms: list[dict[str, object]] = []

        def add(atom_id: str, category: str, fragment_id: int, quote: str, payload: object) -> None:
            atoms.append(
                {
                    "atom_id": atom_id,
                    "category": category,
                    "fragment_id": fragment_id,
                    "quote": quote,
                    "parsed_value": payload.model_dump(mode="json")
                    if isinstance(payload, BaseModel)
                    else payload,
                }
            )

        for role, references in (("requirement", self.requirements), ("preference", self.preferences)):
            for index, criterion_ref in enumerate(references.character, start=1):
                add(
                    f"{role}.character.{index}",
                    f"{role}_character",
                    criterion_ref.fragment_id,
                    criterion_ref.question_quote,
                    criterion_ref,
                )
            for index, compatibility_ref in enumerate(references.compatibility, start=1):
                add(
                    f"{role}.compatibility.{index}",
                    f"{role}_compatibility",
                    compatibility_ref.fragment_id,
                    compatibility_ref.question_quote,
                    compatibility_ref,
                )
        for index, household_ref in enumerate(self.household_facts, start=1):
            add(
                f"household_fact.{index}",
                "household_fact",
                household_ref.fragment_id,
                household_ref.question_quote,
                household_ref,
            )
        ref_groups = (
            ("requested_availability", "requested_availability", self.requested_availability),
            ("requested_compatibility", "requested_compatibility", self.requested_compatibility),
            ("requested_care", "requested_care", self.requested_care),
            ("unsupported_care", "unsupported_care", self.unsupported_care),
            ("requested_pair_lists", "requested_pair_list", self.requested_pair_lists),
        )
        for prefix, category, values in ref_groups:
            for index, requested_ref in enumerate(values, start=1):
                add(
                    f"{prefix}.{index}",
                    category,
                    requested_ref.fragment_id,
                    fragments[requested_ref.fragment_id],
                    requested_ref,
                )
        for atom_id, category, named_ref in (
            ("named_stone", "named_stone", self.named_stone),
            ("recommendation_target", "recommendation_target", self.recommendation_target),
            ("requested_stone_info", "requested_stone_info", self.requested_stone_info),
        ):
            if named_ref is not None:
                add(
                    atom_id,
                    category,
                    named_ref.fragment_id,
                    fragments[named_ref.fragment_id],
                    named_ref,
                )
        candidate_type = self.retrieval.candidate_type if self.retrieval else None
        if candidate_type is not None:
            add("retrieval.candidate_type", "candidate_type", candidate_type.fragment_id,
                fragments[candidate_type.fragment_id], candidate_type)
        return atoms

    def grounding_proposals(self, fragments: Mapping[int, str]) -> list[GroundingProposal]:
        proposals = [
            GroundingProposal(
                proposal_id=f"agreement:{index}",
                concept_id=fact.fact_type.value,
                fragment_id=fact.fragment_id,
                question_quote=fact.question_quote,
                proposed_value=fact.value,
                applies_to_pair=fact.applies_to_pair,
            )
            for index, fact in enumerate(self.household_facts)
            if fact.fact_type is not None
        ]
        candidate = self.retrieval.candidate_type if self.retrieval else None
        if candidate is not None:
            proposals.append(
                GroundingProposal(
                    proposal_id="candidate_type",
                    concept_id="candidate_type",
                    fragment_id=candidate.fragment_id,
                    question_quote=fragments[candidate.fragment_id],
                    proposed_type=candidate.stone_type,
                )
            )
        return proposals

    def grounding_diagnostics(
        self, fragments: Mapping[int, str], supported: frozenset[str]
    ) -> list[dict[str, object]]:
        return [
            {
                "kind": "unsupported_candidate_type"
                if p.concept_id == "candidate_type"
                else "unsupported_agreement",
                **p.model_dump(mode="json"),
            }
            for p in self.grounding_proposals(fragments)
            if p.proposal_id not in supported
        ]

    def resolve_references(self, fragments: Mapping[int, str]) -> ReferenceRequest:
        name = None
        if self.named_stone is not None:
            name = self.named_stone.name.strip()
            if (
                not name
                or name.casefold() not in fragments[self.named_stone.fragment_id].casefold()
            ):
                raise ValueError("Stone name must occur in its question fragment")
        recommendation_name = None
        if self.recommendation_target is not None:
            if self.recommendation_target.fragment_id not in fragments:
                raise KeyError(self.recommendation_target.fragment_id)
            recommendation_name = self.recommendation_target.name.strip()
            if (
                not recommendation_name
                or recommendation_name.casefold()
                not in fragments[self.recommendation_target.fragment_id].casefold()
            ):
                raise ValueError("Recommendation name must occur in its question fragment")
        for item in [
            *self.requested_compatibility,
            *self.requested_care,
            *self.requested_pair_lists,
            *self.unsupported_care,
        ]:
            if item.fragment_id not in fragments:
                raise KeyError(item.fragment_id)
        for item in self.requested_compatibility:
            if item.target == "candidate":
                if item.first_type is not None or not self.recommendation_limit:
                    raise ValueError("Candidate compatibility needs an active recommendation")
            elif item.target == "named_stone":
                if item.first_type is not None or self.named_stone is None:
                    raise ValueError("Named-stone compatibility needs a named individual")
            elif item.first_type is None:
                raise ValueError("Type compatibility needs both explicit types")
        if self.requested_stone_info is not None:
            if self.requested_stone_info.fragment_id not in fragments:
                raise KeyError(self.requested_stone_info.fragment_id)
            if name is None:
                raise ValueError("A named stone is required for individual information")
        for unknown in self.unsupported_care:
            if unknown.material.casefold() not in fragments[unknown.fragment_id].casefold():
                raise ValueError("Unsupported material must occur in its question fragment")
            if unknown.material.upper() in StoneType.__members__:
                raise ValueError("Known materials must use requested_care")
        return ReferenceRequest(
            stone_name=name,
            recommendation_name=recommendation_name,
            stone_info=self.requested_stone_info.topic if self.requested_stone_info else None,
            unsupported_care=list(dict.fromkeys(item.material for item in self.unsupported_care)),
            care_types=list(dict.fromkeys(item.stone_type for item in self.requested_care)),
            pairs=[
                RequestedPair(first_type=first, second_type=second)
                for first, second in dict.fromkeys(
                    (item.first_type, item.household_type)
                    for item in self.requested_compatibility
                    if item.target in ("named_stone", "types")
                )
            ],
            pair_lists=[
                RequestedPairList(stone_type=kind, verdict=verdict)
                for kind, verdict in dict.fromkeys(
                    (item.stone_type, item.verdict) for item in self.requested_pair_lists
                )
            ],
        )

    def resolve(
        self, fragments: Mapping[int, str], supported: frozenset[str] = frozenset()
    ) -> tuple[SearchCriteria, int]:
        for fact in self.household_facts:
            if fact.fragment_id not in fragments or fact.question_quote not in fragments[fact.fragment_id]:
                raise ValueError("Household fact quote must be a source-bound original subquote")
        requirements = self.requirements.resolve(fragments, group_id="requirement")
        preferences = self.preferences.resolve(fragments, group_id="preference")
        required_character = {
            (item.fragment_id, item.question_quote): item for item in requirements.character
        }
        required_compatibility = {
            (item.fragment_id, item.question_quote, item.household_type): item
            for item in requirements.compatibility
        }
        preferred_character = {
            (item.fragment_id, item.question_quote): item
            for item in preferences.character
            if (item.fragment_id, item.question_quote) not in required_character
        }
        preferred_compatibility = {
            (item.fragment_id, item.question_quote, item.household_type): item
            for item in preferences.compatibility
            if (item.fragment_id, item.question_quote, item.household_type)
            not in required_compatibility
        }
        duplicates_removed = (
            len(requirements.character)
            + len(requirements.compatibility)
            + len(preferences.character)
            + len(preferences.compatibility)
            - len(required_character)
            - len(required_compatibility)
            - len(preferred_character)
            - len(preferred_compatibility)
        )
        criteria = SearchCriteria(
            recommendation_limit=min(self.recommendation_limit, RANKING_POLICY.shortlist_limit),
            requested_availability=[
                QuotedCriterion(
                    criterion_id=f"requested_availability.{index}",
                    fragment_id=item.fragment_id, question_quote=fragments[item.fragment_id]
                )
                for index, item in enumerate(self.requested_availability, start=1)
            ],
            requested_compatibility=[
                CompatibilityCriterion(
                    criterion_id=f"requested_compatibility.{index}",
                    fragment_id=item.fragment_id,
                    question_quote=fragments[item.fragment_id],
                    household_type=item.household_type,
                )
                for index, item in enumerate(self.requested_compatibility, start=1)
                if item.target == "candidate"
            ],
            household_facts=[
                HouseholdFact(
                    criterion_id=f"household_fact.{index + 1}",
                    question_quote=item.question_quote,
                    **item.model_dump(exclude={"question_quote"}),
                )
                for index, item in enumerate(self.household_facts)
                if item.fact_type is None or f"agreement:{index}" in supported
            ],
            requirements=CriteriaGroup(
                character=list(required_character.values()),
                compatibility=list(required_compatibility.values()),
            ),
            preferences=CriteriaGroup(
                character=list(preferred_character.values()),
                compatibility=list(preferred_compatibility.values()),
            ),
        )
        return criteria, duplicates_removed


def validate_parsed_atoms(
    atoms: list[dict[str, object]], fragments: Mapping[int, str]
) -> None:
    """Reject parser atoms that are blank or not bound to their source fragment."""
    atom_ids: set[str] = set()
    for atom in atoms:
        atom_id = atom.get("atom_id")
        fragment_id = atom.get("fragment_id")
        quote = atom.get("quote")
        if not isinstance(atom_id, str) or not atom_id or atom_id in atom_ids:
            raise ValueError("Parsed atom IDs must be present and unique")
        atom_ids.add(atom_id)
        if not isinstance(fragment_id, int) or fragment_id not in fragments:
            raise ValueError("Parsed atom must reference a known question fragment")
        if not isinstance(quote, str) or not quote.strip() or quote not in fragments[fragment_id]:
            raise ValueError("Parsed atom quote must be a nonblank original subquote")


class SelectCandidates(BaseModel):
    """Return candidate IDs from the retrieved cards in preference order."""

    model_config = ConfigDict(extra="forbid", strict=True)

    stone_ids: list[str]


def question_fragments(question: str) -> dict[int, str]:
    """Number verbatim clauses and lines, keeping punctuation and original language."""
    fragments = (part.strip() for part in re.split(r"(?<=[.!?;,:])\s+|\n+", question))
    return dict(enumerate((fragment for fragment in fragments if fragment), start=1))
