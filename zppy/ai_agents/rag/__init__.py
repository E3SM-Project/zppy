"""
RAG (Retrieval-Augmented Generation) module for zppy.

Provides vector-based search over zppy documentation, parameters,
and example configurations.
"""

__all__ = ["ZppyRAGIndexer", "ZppyRAGQuerier"]


def __getattr__(name):
    if name == "ZppyRAGIndexer":
        from zppy.ai_agents.rag.indexer import ZppyRAGIndexer

        return ZppyRAGIndexer
    if name == "ZppyRAGQuerier":
        from zppy.ai_agents.rag.querier import ZppyRAGQuerier

        return ZppyRAGQuerier
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
