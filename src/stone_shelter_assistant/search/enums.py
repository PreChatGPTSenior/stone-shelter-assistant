"""Kinds of evidence represented by search documents."""

from enum import StrEnum


class DocumentKind(StrEnum):
    STONE = "stone"
    PROFILE = "profile"
    CASE_EVENT = "case_event"
    ENCYCLOPEDIA_SECTION = "encyclopedia_section"
