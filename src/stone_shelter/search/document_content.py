"""Format and hash the text used by search documents."""

from hashlib import sha256


def build_embedding_text(title: str, text: str) -> str:
    """Combine a document title and body in the format sent to the embedding model."""
    return f"{title}\n\n{text}"


def calculate_text_hash(text: str) -> str:
    """Return a SHA-256 digest of UTF-8 text with its algorithm prefix."""
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"
