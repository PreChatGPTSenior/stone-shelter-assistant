"""Create the asynchronous Typesense client."""

from typesense import AsyncClient

from stone_shelter.settings import TypesenseSettings


def create_typesense_client(settings: TypesenseSettings) -> AsyncClient:
    """Create a client whose lifecycle is owned by the caller.

    Args:
        settings: Validated Typesense connection settings.

    Returns:
        An asynchronous client configured without automatic request retries.
    """
    return AsyncClient(
        {
            "nodes": [
                {
                    "host": settings.host,
                    "port": settings.port,
                    "protocol": settings.protocol,
                }
            ],
            "api_key": settings.api_key.get_secret_value(),
            "connection_timeout_seconds": settings.connection_timeout_seconds,
            "num_retries": 0,
        }
    )
