from pathlib import Path

from stone_shelter.catalog.enums import StoneType
from stone_shelter.search.encyclopedia import build_encyclopedia_documents

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SOURCE_PATH = "stone-rules/stone-encyclopedias/stone-encyclopedia_en.md"


def test_build_encyclopedia_documents_from_real_source() -> None:
    markdown = (PROJECT_ROOT / SOURCE_PATH).read_text(encoding="utf-8")

    documents = build_encyclopedia_documents(
        markdown=markdown,
        source_path=SOURCE_PATH,
    )
    # For the pilot, we selected ten rock-type chapters and four general sections.

    rock_titles = {
        "Basalt",
        "Granite",
        "Obsidian",
        "Pumice",
        "Limestone",
        "Sandstone",
        "Shale",
        "Marble",
        "Gneiss",
        "Slate",
    }

    general_titles = {
        "About This Guide",
        "Rating Scales",
        "Quick Comparison",
        "General Care Rules",
    }

    expected_titles = rock_titles | general_titles

    assert len(documents) == 14
    assert {document.title for document in documents} == expected_titles
    assert len({document.id for document in documents}) == 14

    documents_by_title = {document.title: document for document in documents}

    for title, document in documents_by_title.items():
        assert document.section_path == [title], title
        assert document.source_path == SOURCE_PATH, title
        assert document.text.strip(), title

        if title in rock_titles:
            assert document.stone_type == StoneType[title.upper()], title
            assert document.section_path == [title], title
            assert f"**Common name:** {title.lower()}" in document.text, title
            assert "### Geological Profile" in document.text
            assert "### Fictional Care Ritual" in document.text
        else:
            assert document.stone_type is None, title
