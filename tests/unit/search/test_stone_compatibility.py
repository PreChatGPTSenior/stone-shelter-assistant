from itertools import combinations_with_replacement
from pathlib import Path

from stone_shelter_assistant.search.document_models import (
    CompatibilityPairSearchDocument,
    CompatibilityReadingRulesSearchDocument,
    CompatibilityTypePortraitSearchDocument,
)
from stone_shelter_assistant.search.knowledge.stone_compatibility_document_builder import (
    build_stone_compatibility_documents,
)
from stone_shelter_assistant.stones.enums import StoneType

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SOURCE_PATH = "fixtures/knowledge/type-compatibility/stone-type-compatibility_en.json"


def test_build_compatibility_documents_from_real_source() -> None:
    json_text = (PROJECT_ROOT / SOURCE_PATH).read_text(encoding="utf-8")

    documents = build_stone_compatibility_documents(
        json_text=json_text,
        source_path=SOURCE_PATH,
    )

    pairs = [doc for doc in documents if isinstance(doc, CompatibilityPairSearchDocument)]
    portraits = [
        doc for doc in documents if isinstance(doc, CompatibilityTypePortraitSearchDocument)
    ]
    rules = [doc for doc in documents if isinstance(doc, CompatibilityReadingRulesSearchDocument)]

    assert len(pairs) == 55
    assert len(portraits) == 10
    assert len(rules) == 1

    assert {tuple(doc.stone_types) for doc in portraits} == {
        (stone_type,) for stone_type in StoneType
    }

    expected_pairs = set(combinations_with_replacement(sorted(StoneType), 2))
    actual_pairs = {tuple(sorted(doc.stone_types)) for doc in pairs}
    assert actual_pairs == expected_pairs

    assert all(doc.source_path == SOURCE_PATH for doc in documents)

    ids_by_key = {doc.source_key: doc.id for doc in documents}
    assert len(ids_by_key) == len(documents)
    assert len(set(ids_by_key.values())) == len(documents)

    rebuilt = build_stone_compatibility_documents(
        json_text=json_text,
        source_path=SOURCE_PATH,
    )
    assert {doc.source_key: doc.id for doc in rebuilt} == ids_by_key

    assert len(documents) == 66
