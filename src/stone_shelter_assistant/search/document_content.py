"""Format values used in search documents."""

from datetime import UTC, datetime, timedelta
from hashlib import sha256

_UNIX_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def build_embedding_text(title: str, text: str) -> str:
    """Combine a document title and body in the format sent to the embedding model."""
    return f"{title}\n\n{text}"


def calculate_text_hash(text: str) -> str:
    """Return a SHA-256 digest of UTF-8 text with its algorithm prefix."""
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


def to_unix_microseconds(value: datetime) -> int:
    """Use the same timestamp representation for indexed events and date filters."""
    return (value - _UNIX_EPOCH) // timedelta(microseconds=1)
