"""Typed semantic decisions and exact binding checks; no lexical phrase rules."""

from collections.abc import Mapping
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator

from stone_shelter_assistant.stones.enums import StoneType


class GroundingProposal(BaseModel):
    proposal_id: str
    concept_id: str
    fragment_id: int = Field(ge=1)
    question_quote: str = Field(min_length=1)
    proposed_type: StoneType | None = None
    proposed_value: StrictBool | None = None
    applies_to_pair: tuple[StoneType, StoneType] | None = None


class GroundingDecision(BaseModel):
    proposal_id: str
    finding: Literal["supported", "contradicted", "unknown"]
    fragment_id: int = Field(ge=1)
    quote: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class CoverageIssueBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str
    atom_id: str | None = None
    fragment_id: int | None = Field(default=None, ge=1)
    quote: str | None = None
    reason: str = Field(min_length=1)

    @field_validator("reason")
    @classmethod
    def reason_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Coverage issue reason must not be blank")
        return value


class OmittedCoverageIssue(CoverageIssueBase):
    kind: Literal["omitted"]
    atom_id: None = None
    fragment_id: int = Field(ge=1)
    quote: str = Field(min_length=1)


class MisclassifiedCoverageIssue(CoverageIssueBase):
    kind: Literal["misclassified"]
    atom_id: str = Field(min_length=1)
    fragment_id: int = Field(ge=1)
    quote: str = Field(min_length=1)


class UncertainCoverageIssue(CoverageIssueBase):
    kind: Literal["uncertain"]


QuestionCoverageIssue = Annotated[
    OmittedCoverageIssue | MisclassifiedCoverageIssue | UncertainCoverageIssue,
    Field(discriminator="kind"),
]


class QuestionCoverageAudit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["complete", "incomplete", "uncertain"]
    summary: str = Field(min_length=1)
    issues: list[QuestionCoverageIssue] = Field(default_factory=list)

    @field_validator("summary")
    @classmethod
    def summary_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Coverage summary must not be blank")
        return value


class GroundingResponse(BaseModel):
    decisions: list[GroundingDecision]
    question_coverage: QuestionCoverageAudit


def validate_grounding_response(
    response: GroundingResponse,
    proposals: list[GroundingProposal],
    fragments: Mapping[int, str],
) -> frozenset[str]:
    """Require complete, unique decisions bound to their original question fragments."""
    by_id = {proposal.proposal_id: proposal for proposal in proposals}
    ids = [decision.proposal_id for decision in response.decisions]
    if len(ids) != len(set(ids)) or set(ids) != set(by_id):
        raise ValueError("Grounding decisions must cover every proposal exactly once")
    for decision in response.decisions:
        proposal = by_id[decision.proposal_id]
        if (
            decision.fragment_id != proposal.fragment_id
            or not decision.quote.strip()
            or decision.quote != proposal.question_quote
            or decision.quote not in fragments[proposal.fragment_id]
        ):
            raise ValueError("Grounding quote must bind to the proposal's original fragment")
    return frozenset(d.proposal_id for d in response.decisions if d.finding == "supported")


def validate_question_coverage(
    audit: QuestionCoverageAudit,
    parsed_atoms: list[dict[str, object]],
    fragments: Mapping[int, str],
) -> None:
    """Check that the audit verdict is justified against the parsed criteria and original question."""
    atom_by_id = {str(atom["atom_id"]): atom for atom in parsed_atoms}
    _require_unique_parsed_atoms(parsed_atoms, atom_by_id)
    _validate_audit_status(audit)
    for issue in audit.issues:
        _validate_issue_binding(issue, atom_by_id, fragments)
    _require_unique_coverage_issues(audit.issues)


def _require_unique_parsed_atoms(
    parsed_atoms: list[dict[str, object]], atom_by_id: Mapping[str, dict[str, object]]
) -> None:
    if len(atom_by_id) != len(parsed_atoms):
        raise ValueError("Parsed atom IDs must be unique")


def _validate_audit_status(audit: QuestionCoverageAudit) -> None:
    match audit.status:
        case "complete" if audit.issues:
            raise ValueError("Complete question coverage cannot include issues")
        case "incomplete" if not any(
            isinstance(issue, (OmittedCoverageIssue, MisclassifiedCoverageIssue))
            for issue in audit.issues
        ):
            raise ValueError("Incomplete coverage needs a bound omission or misclassification")
        case "uncertain" if not any(
            isinstance(issue, UncertainCoverageIssue) for issue in audit.issues
        ):
            raise ValueError("Uncertain coverage needs an explicit uncertainty issue")


def _validate_issue_binding(
    issue: QuestionCoverageIssue,
    atom_by_id: Mapping[str, dict[str, object]],
    fragments: Mapping[int, str],
) -> None:
    _validate_issue_source_quote(issue, fragments)
    _validate_issue_atom(issue, atom_by_id)


def _validate_issue_source_quote(
    issue: QuestionCoverageIssue, fragments: Mapping[int, str]
) -> None:
    if issue.quote is None:
        return
    if issue.fragment_id is None or issue.fragment_id not in fragments:
        raise ValueError("Coverage issue quote needs a known original fragment")
    if issue.quote not in fragments[issue.fragment_id]:
        raise ValueError("Coverage issue quote must be a verbatim original subquote")


def _validate_issue_atom(
    issue: QuestionCoverageIssue, atom_by_id: Mapping[str, dict[str, object]]
) -> None:
    if issue.atom_id is None:
        return
    if issue.atom_id not in atom_by_id:
        raise ValueError("Coverage issue references an unknown parsed atom ID")
    atom = atom_by_id[issue.atom_id]
    if issue.fragment_id is not None and atom.get("fragment_id") != issue.fragment_id:
        raise ValueError("Coverage issue fragment does not match the parsed atom")
    if isinstance(issue, MisclassifiedCoverageIssue) and issue.quote != atom.get("quote"):
        raise ValueError("Misclassified atom quote must match its source-bound atom")


def _require_unique_coverage_issues(issues: list[QuestionCoverageIssue]) -> None:
    keys = [
        (issue.kind, issue.atom_id, issue.fragment_id, issue.quote)
        for issue in issues
    ]
    if len(keys) != len(set(keys)):
        raise ValueError("Coverage issues must be unique")
