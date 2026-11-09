from langchain_ollama import OllamaEmbeddings

from stone_shelter.settings import OllamaEmbeddingSettings


def create_embeddings(settings: OllamaEmbeddingSettings) -> OllamaEmbeddings:
    return OllamaEmbeddings(
        model=settings.embedding_model,
        base_url=settings.base_url,
    )
