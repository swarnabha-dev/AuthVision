"""
Service stub: Embedding extraction service.

TODO: Implement LightCNN-10 + AdaFace wrappers in Modules 5 & 7.
"""


class EmbeddingService:
    """Embedding extraction service (stub implementation)."""

    def __init__(self) -> None:
        """Initialize embedding service."""
        # TODO: Load LightCNN-10 (FFWM) and AdaFace models
        raise NotImplementedError("EmbeddingService not implemented - see Modules 5 & 7")


def get_embedding_service() -> EmbeddingService:
    """Dependency injection for embedding service.

    Returns:
        EmbeddingService instance

    Raises:
        NotImplementedError: Module not yet implemented
    """
    raise NotImplementedError("EmbeddingService not implemented - see Modules 5 & 7")
