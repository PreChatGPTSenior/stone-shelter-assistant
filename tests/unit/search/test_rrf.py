"""Check rank fusion without models, databases or search services."""

from uuid import UUID

import pytest

from stone_shelter_assistant.search.document_models import StoneSearchDocument
from stone_shelter_assistant.search.stones.rrf import fuse_stone_results
from stone_shelter_assistant.search.stones.search_contracts import HybridSearchSettings
from stone_shelter_assistant.stones.enums import AdoptionStatus, StoneSize, StoneType


def card(number: int) -> StoneSearchDocument:
    return StoneSearchDocument(
        id=UUID(int=number + 100),
        stone_external_id=UUID(int=number),
        title=f"Stone {number}",
        text="A quiet companion.",
        language="en",
        source_key=f"stone:{number}",
        schema_version=1,
        projection_version=1,
        source_revision="sha256:" + "0" * 64,
        content_hash="sha256:" + "1" * 64,
        case_external_id=UUID(int=number + 200),
        case_number=f"case-{number}",
        stone_type=StoneType.GRANITE,
        stone_size=StoneSize.SMALL,
        adoption_status=AdoptionStatus.AVAILABLE,
        current_shelter_id=UUID(int=300),
    )


def test_overlap_adds_both_contributions_and_sorts_ties_by_external_id() -> None:
    a, b, c = card(1), card(2), card(3)
    result = fuse_stone_results([b, a, c], [a, b])
    assert [hit.card.id for hit in result.candidates] == [a.id, b.id, c.id]
    a_hit, b_hit, c_hit = result.candidates
    assert (a_hit.lexical_rank, a_hit.semantic_rank) == (2, 1)
    assert a_hit.lexical_contribution == pytest.approx(1 / 62)
    assert a_hit.semantic_contribution == pytest.approx(1 / 61)
    assert a_hit.rrf_score == pytest.approx(0.03252247488101534)
    assert b_hit.rrf_score == a_hit.rrf_score
    assert (c_hit.lexical_rank, c_hit.semantic_rank) == (3, None)
    assert c_hit.semantic_contribution == 0
    assert c_hit.rrf_score == pytest.approx(1 / 63)
    assert [hit.retrieval_rank for hit in result.candidates] == [1, 2, 3]
    assert all(hit.in_pool and not hit.payload_mismatch for hit in result.candidates)


def test_disjoint_lists_keep_both_engines_and_break_ties_independently_of_arrival() -> None:
    a, b = card(1), card(2)
    for lexical, semantic in (([b], [a]), ([a], [b])):
        result = fuse_stone_results(lexical, semantic)
        assert [hit.card.id for hit in result.candidates] == [a.id, b.id]
        assert all(hit.rrf_score == pytest.approx(1 / 61) for hit in result.candidates)


def test_duplicate_does_not_add_votes_or_leave_rank_gaps() -> None:
    a, b = card(1), card(2)
    duplicate = a.model_copy(update={"text": "A later duplicate must not replace the first."})
    result = fuse_stone_results([a, duplicate, b], [b, b, a])
    assert result.lexical_ids == [a.id, b.id]
    assert result.semantic_ids == [b.id, a.id]
    a_hit, b_hit = result.candidates
    assert a_hit.card.text == a.text
    assert (b_hit.lexical_rank, b_hit.semantic_rank) == (2, 1)
    assert a_hit.rrf_score == pytest.approx(1 / 61 + 1 / 62)
    assert b_hit.rrf_score == a_hit.rrf_score
    assert not a_hit.payload_mismatch


@pytest.mark.parametrize("engine", ["lexical", "semantic"])
def test_one_empty_engine_preserves_other_order_and_custom_k(engine: str) -> None:
    a, b = card(1), card(2)
    cards = [b, a]
    result = fuse_stone_results(
        cards if engine == "lexical" else [],
        cards if engine == "semantic" else [],
        HybridSearchSettings(rrf_k=10),
    )
    assert [hit.card.id for hit in result.candidates] == [b.id, a.id]
    assert [hit.rrf_score for hit in result.candidates] == pytest.approx([1 / 11, 1 / 12])


def test_both_empty_engines_return_empty_result() -> None:
    result = fuse_stone_results([], [])
    assert result.candidates == result.dropped == result.lexical_ids == result.semantic_ids == []


def test_pool_cutoff_preserves_dropped_hits_and_engine_provenance() -> None:
    a, b, c = card(1), card(2), card(3)
    result = fuse_stone_results([a, b], [a, c], HybridSearchSettings(pool_limit=1))
    assert [hit.card.id for hit in result.candidates] == [a.id]
    assert [hit.card.id for hit in result.dropped] == [b.id, c.id]
    assert [hit.retrieval_rank for hit in result.dropped] == [2, 3]
    assert all(not hit.in_pool for hit in result.dropped)
    assert result.lexical_ids == [a.id, b.id]
    assert result.semantic_ids == [a.id, c.id]
    assert result.dropped[0].rrf_score == pytest.approx(1 / 62)
    assert result.model_dump(mode="json")["dropped"][0]["card"]["id"] == str(b.id)


def test_payload_conflict_keeps_typesense_card_without_changing_inputs() -> None:
    a = card(1)
    semantic_card = a.model_copy(update={"text": "Stale vector payload."})
    lexical, semantic = [a], [semantic_card]
    result = fuse_stone_results(lexical, semantic)
    assert result.candidates[0].payload_mismatch
    assert result.candidates[0].card.text == "A quiet companion."
    assert semantic[0].text == "Stale vector payload."
    assert lexical == [a]


def test_sort_does_not_round_away_small_score_differences() -> None:
    a, b = card(1), card(2)
    result = fuse_stone_results([b, a], [], HybridSearchSettings(rrf_k=1_000_000))
    assert [hit.card.id for hit in result.candidates] == [b.id, a.id]
    assert result.candidates[0].rrf_score > result.candidates[1].rrf_score
