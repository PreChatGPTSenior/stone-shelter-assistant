"""Build search documents from the authored stone type compatibility guide."""

import json
from uuid import NAMESPACE_URL, uuid5

from stone_shelter_assistant.search.document_content import (
    build_embedding_text,
    calculate_text_hash,
)
from stone_shelter_assistant.search.document_models import (
    PROJECTION_VERSION,
    SEARCH_SCHEMA_VERSION,
    CompatibilityPairSearchDocument,
    CompatibilityReadingRulesSearchDocument,
    CompatibilitySearchDocument,
    CompatibilityTypePortraitSearchDocument,
)
from stone_shelter_assistant.stones.enums import StoneType


def build_stone_compatibility_documents(
    json_text: str,
    source_path: str,
) -> list[CompatibilitySearchDocument]:
    """Build one document for the rules and one for each portrait and pairing."""
    sections = json.loads(json_text)
    documents: list[CompatibilitySearchDocument] = []
    language = sections["language"]
    key_prefix = f"compatibility:{sections['catalog_id']}:{language}"
    source_revision = calculate_text_hash(json_text)

    def build_common_document(
        *, title: str, text: str, source_key: str
    ) -> CompatibilitySearchDocument:
        return CompatibilitySearchDocument(
            id=uuid5(
                NAMESPACE_URL,
                f"urn:stone-shelter-assistant:search-document:{source_key}",
            ),
            title=title,
            text=text,
            language=language,
            source_key=source_key,
            source_path=source_path,
            schema_version=SEARCH_SCHEMA_VERSION,
            projection_version=PROJECTION_VERSION,
            source_revision=source_revision,
            content_hash=calculate_text_hash(build_embedding_text(title, text)),
        )

    documents.append(
        CompatibilityReadingRulesSearchDocument(
            **build_common_document(
                title=f"{sections['title']} — Reading rules",
                text="\n".join(f"- {rule}" for rule in sections["reading_rules"]),
                source_key=f"{key_prefix}:reading-rules",
            ).model_dump(),
        )
    )

    for portrait in sections["type_portraits"]:
        stone_type = StoneType(portrait["stone_type"])
        documents.append(
            CompatibilityTypePortraitSearchDocument(
                **build_common_document(
                    title=f"{stone_type.value.title()} — {portrait['nickname']}",
                    text=(
                        f"Temperament: {portrait['temperament']}\n"
                        f"Comforts: {portrait['comforts']}\n"
                        f"Sensitivities: {portrait['sensitivities']}"
                    ),
                    source_key=f"{key_prefix}:portrait:{stone_type.value.lower()}",
                ).model_dump(),
                stone_types=[stone_type],
            )
        )

    for pair in sections["pairings"]:
        stone_types = [StoneType(value) for value in pair["stone_types"]]
        pair_name = " + ".join(stone_type.value.title() for stone_type in stone_types)
        documents.append(
            CompatibilityPairSearchDocument(
                **build_common_document(
                    title=f"{pair_name} — {pair['title']}",
                    text=(
                        f"Verdict: {pair['verdict']}\n"
                        f"Explanation: {pair['explanation']}\n"
                        f"Household agreement: {pair['household_agreement']}\n"
                        f"Avoid: {pair['avoid']}\n"
                        f"Bureau note: {pair['bureau_note']}"
                    ),
                    source_key=f"{key_prefix}:pair:{pair['id']}",
                ).model_dump(),
                stone_types=stone_types,
            )
        )

    return documents
