"""Kinds of evidence represented by search documents."""

from enum import StrEnum


class DocumentKind(StrEnum):
    STONE = "stone"
    CASE_EVENT = "case_event"
    ENCYCLOPEDIA_SECTION = "encyclopedia_section"
    COMPATIBILITY_PAIR = "compatibility_pair"
    COMPATIBILITY_TYPE_PORTRAIT = "compatibility_type_portrait"
    COMPATIBILITY_READING_RULES = "compatibility_reading_rules"


class CompatibilityVerdict(StrEnum):
    HARMONIOUS = "HARMONIOUS"
    CONDITIONAL = "CONDITIONAL"
    NOT_RECOMMENDED = "NOT_RECOMMENDED"


class AccommodationFactType(StrEnum):
    DECISION_ROTATION_AGREED = "decision_rotation_agreed"
    DECISION_DEADLINE_AGREED = "decision_deadline_agreed"
