from stone_shelter_assistant.assistant.candidate_evidence import (
    SourceText,
    assessment_source_text,
)


def test_assessment_context_preserves_conflicting_evidence_and_source_references() -> None:
    chapter = (
        "**Character archetype:** lively companion.\n\n"
        "### Geological Profile\nGeological details.\n\n"
        "### Ideal Places at Home\nNeeds an active household.\n\n"
        "### Psychological Vibe\nDislikes quiet evenings.\n\n"
        "### Daily Care\nCleaning instructions.\n"
    )
    sources = {
        "profile.preferred_environment": SourceText(
            "profile", "stone-card:one", "preferred_environment", "Prefers a quiet home."
        ),
        "biography": SourceText(
            "biography", "stone-card:one", "biography", "Enjoys noisy company."
        ),
        "encyclopedia": SourceText("encyclopedia", "encyclopedia:one", "text", chapter),
    }
    context = {ref: assessment_source_text(source) for ref, source in sources.items()}
    assert context["profile.preferred_environment"] == "Prefers a quiet home."
    assert context["biography"] == "Enjoys noisy company."
    assert "Needs an active household." in context["encyclopedia"]
    assert "Dislikes quiet evenings." in context["encyclopedia"]
    assert "Geological details." not in context["encyclopedia"]
    assert "Cleaning instructions." not in context["encyclopedia"]
    assert sources["encyclopedia"].source_id == "encyclopedia:one"
    assert sources["encyclopedia"].text == chapter


def test_unstructured_encyclopedia_retains_original_evidence() -> None:
    source = SourceText("encyclopedia", "encyclopedia:legacy", "text", "Prefers active company.")
    assert assessment_source_text(source) == source.text
