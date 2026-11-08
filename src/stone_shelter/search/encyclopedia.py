"""Prepare search documents from the English stone encyclopedia."""

from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

from langchain_text_splitters import MarkdownHeaderTextSplitter

from stone_shelter.catalog.enums import StoneType
from stone_shelter.search.documents import EncyclopediaSectionSearchDocument

GENERAL_SECTIONS = {
    "About This Guide",
    "Rating Scales",
    "Quick Comparison",
    "General Care Rules",
}


def build_encyclopedia_documents(
    markdown: str,
    source_path: str,
) -> list[EncyclopediaSectionSearchDocument]:
    """Build one search document per selected encyclopedia chapter.

    Split the known English encyclopedia at level-two headings.
    Keep nested headings and their content within each chapter.
    LangChain normalizes whitespace in the resulting text.

    Args:
        markdown: Complete Markdown source text.
        source_path: Repository-relative path used for source references.

    Returns:
        Search documents for rock-type chapters and selected general sections.
    """
    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("##", "section")],
        strip_headers=True,
    )
    sections = splitter.split_text(markdown)

    stone_types_by_title = {stone_type.value.title(): stone_type for stone_type in StoneType}
    source_revision = f"sha256:{sha256(markdown.encode('utf-8')).hexdigest()}"
    documents: list[EncyclopediaSectionSearchDocument] = []

    for section in sections:
        title = section.metadata.get("section")

        # Introductory text before the first section has no section heading.
        if not isinstance(title, str):
            continue

        if title not in GENERAL_SECTIONS and title not in stone_types_by_title:
            continue

        text = section.page_content
        section_key = title.lower().replace(" ", "-")
        source_key = f"encyclopedia:en:{section_key}"
        embedding_text = f"{title}\n\n{text}"
        content_hash = f"sha256:{sha256(embedding_text.encode('utf-8')).hexdigest()}"

        document = EncyclopediaSectionSearchDocument(
            id=uuid5(
                NAMESPACE_URL,
                f"urn:stone-shelter:search-document:{source_key}",
            ),
            title=title,
            text=text,
            language="en",
            source_key=source_key,
            schema_version=1,
            projection_version=1,
            source_revision=source_revision,
            content_hash=content_hash,
            source_path=source_path,
            section_path=[title],
            stone_type=stone_types_by_title.get(title),
        )
        documents.append(document)

    return documents
