"""Pure rank fusion of already retrieved stone cards."""

from collections.abc import Sequence
from uuid import UUID

from stone_shelter_assistant.search.document_models import StoneSearchDocument
from stone_shelter_assistant.search.stones.search_contracts import (
    HybridSearchResult,
    HybridSearchSettings,
    HybridStoneHit,
)


def _unique_cards(cards: Sequence[StoneSearchDocument]) -> dict[UUID, StoneSearchDocument]:
    """Keep each stone's first payload and its original order."""
    unique: dict[UUID, StoneSearchDocument] = {}
    for card in cards:
        unique.setdefault(card.id, card)
    return unique


def fuse_stone_results(
    lexical: Sequence[StoneSearchDocument],
    semantic: Sequence[StoneSearchDocument],
    settings: HybridSearchSettings | None = None,
) -> HybridSearchResult:
    """Fuse bounded engine lists; deduplicate before assigning one-based ranks.

    Backend orchestration owns per_engine_limit. This function preserves every
    distinct received hit and applies only the final pool cutoff.
    """
    settings = HybridSearchSettings() if settings is None else settings
    lexical_cards = _unique_cards(lexical)
    semantic_cards = _unique_cards(semantic)
    lexical_ids = list(lexical_cards)
    semantic_ids = list(semantic_cards)
    lexical_ranks = {stone_id: rank for rank, stone_id in enumerate(lexical_ids, start=1)}
    semantic_ranks = {stone_id: rank for rank, stone_id in enumerate(semantic_ids, start=1)}
    hits = []
    for stone_id in dict.fromkeys([*lexical_ids, *semantic_ids]):
        lexical_card = lexical_cards.get(stone_id)
        semantic_card = semantic_cards.get(stone_id)
        card = lexical_card if lexical_card is not None else semantic_cards[stone_id]
        lexical_rank = lexical_ranks.get(stone_id)
        semantic_rank = semantic_ranks.get(stone_id)
        lexical_contribution = 1 / (settings.rrf_k + lexical_rank) if lexical_rank else 0.0
        semantic_contribution = 1 / (settings.rrf_k + semantic_rank) if semantic_rank else 0.0
        hits.append(
            HybridStoneHit(
                card=card,
                lexical_rank=lexical_rank,
                semantic_rank=semantic_rank,
                lexical_contribution=lexical_contribution,
                semantic_contribution=semantic_contribution,
                rrf_score=lexical_contribution + semantic_contribution,
                retrieval_rank=0,
                payload_mismatch=(
                    lexical_card is not None
                    and semantic_card is not None
                    and lexical_card != semantic_card
                ),
                in_pool=False,
            )
        )
    hits.sort(key=lambda hit: (-hit.rrf_score, str(hit.card.stone_external_id)))
    ranked = [
        hit.model_copy(update={"retrieval_rank": rank, "in_pool": rank <= settings.pool_limit})
        for rank, hit in enumerate(hits, start=1)
    ]
    return HybridSearchResult(
        settings=settings,
        lexical_ids=lexical_ids,
        semantic_ids=semantic_ids,
        candidates=ranked[: settings.pool_limit],
        dropped=ranked[settings.pool_limit :],
    )
