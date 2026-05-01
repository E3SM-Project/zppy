"""
RAG Querier for zppy documentation, parameters, and examples.

This module handles querying the vector database built by the indexer
to retrieve relevant context for AI-assisted configuration.
"""

import os
from typing import List, Optional, Any, Dict
from dataclasses import dataclass

# Collection names must match those used in indexer.py
COLLECTION_NAMES = ["zppy_parameters", "zppy_examples", "zppy_docs"]


@dataclass
class QueryResult:
    """A single result from a RAG query."""

    text: str
    metadata: Dict[str, Any]
    distance: float
    collection: str


class ZppyRAGQuerier:
    """
    Queries zppy content indexed by ZppyRAGIndexer.

    Searches three ChromaDB collections:
    1. zppy_parameters: Parameter definitions from default.ini
    2. zppy_examples: Example configurations from tests/integration/
    3. zppy_docs: Documentation from docs/source/

    Usage:
        querier = ZppyRAGQuerier()
        results = querier.query("how to configure climo years")
    """

    # TODO: Switch back to sentence-transformers embeddings when e3sm-unified
    # includes PyTorch. sentence-transformers provides higher quality embeddings
    # (model: all-MiniLM-L6-v2) but pulls in PyTorch (~2GB) which is not yet
    # available in e3sm-unified. For now, we use ChromaDB's built-in default
    # embedding function (ONNX-based) to avoid this heavy dependency.
    #
    # To revert, restore the `embedder` property and pass explicit
    # `query_embeddings=[self.embedder.encode(question).tolist()]` to
    # collection.query() instead of `query_texts=[question]`.

    def __init__(
        self,
        db_path: Optional[str] = None,
    ):
        """
        Initialize the RAG querier.

        Args:
            db_path: Path to the vector database (default: ~/.zppy-ai/vector_db)
        """
        self.db_path = db_path or os.path.expanduser("~/.zppy-ai/vector_db")

        # Lazy-loaded components
        self._client = None
        self._embedding_fn = None

    @property
    def client(self):
        """Lazy-load the ChromaDB client."""
        if self._client is None:
            try:
                import chromadb

                self._client = chromadb.PersistentClient(path=self.db_path)
            except ImportError:
                raise ImportError(
                    "chromadb is required. "
                    "Install with: pip install chromadb"
                )
        return self._client

    @property
    def embedding_fn(self):
        """Lazy-load the ONNX embedding function.

        Must match the function used in ZppyRAGIndexer so query vectors
        are comparable to indexed vectors. Severity 4 (Fatal) suppresses
        ONNX Runtime's Error-level thread-affinity warnings on HPC login nodes.
        """
        if self._embedding_fn is None:
            import onnxruntime as ort
            ort.set_default_logger_severity(4)
            from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
            self._embedding_fn = ONNXMiniLM_L6_V2()
        return self._embedding_fn

    def query(
        self,
        question: str,
        n_results: int = 5,
        collections: Optional[List[str]] = None,
    ) -> List[QueryResult]:
        """
        Query the vector database for relevant content.

        Args:
            question: Natural language query
            n_results: Number of results per collection
            collections: Collection names to search (default: all three)

        Returns:
            List of QueryResult sorted by relevance (lowest distance first)
        """
        target_collections = collections or COLLECTION_NAMES

        all_results = []
        for col_name in target_collections:
            try:
                collection = self.client.get_collection(
                    col_name, embedding_function=self.embedding_fn
                )
            except Exception:
                continue  # Collection not yet indexed

            # Use ChromaDB's default embedding to vectorize the query text
            results = collection.query(
                query_texts=[question],
                n_results=n_results,
            )

            # ChromaDB returns lists of lists; unpack the outer list
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]

            for text, metadata, distance in zip(documents, metadatas, distances):
                all_results.append(
                    QueryResult(
                        text=text,
                        metadata=metadata or {},
                        distance=distance,
                        collection=col_name,
                    )
                )

        # Sort by distance (lower = more relevant)
        all_results.sort(key=lambda r: r.distance)
        return all_results

    def query_parameters(
        self, question: str, n_results: int = 5
    ) -> List[QueryResult]:
        """Query only the zppy_parameters collection."""
        return self.query(question, n_results, collections=["zppy_parameters"])

    def query_examples(
        self, question: str, n_results: int = 5
    ) -> List[QueryResult]:
        """Query only the zppy_examples collection."""
        return self.query(question, n_results, collections=["zppy_examples"])

    def query_docs(self, question: str, n_results: int = 5) -> List[QueryResult]:
        """Query only the zppy_docs collection."""
        return self.query(question, n_results, collections=["zppy_docs"])

    def get_context_for_llm(
        self, question: str, max_tokens: int = 3000, n_results: int = 5
    ) -> str:
        """
        Query all collections and format results into a context string
        suitable for including in an LLM prompt.

        Args:
            question: Natural language query
            max_tokens: Approximate token limit (uses ~4 chars per token estimate)
            n_results: Number of results per collection

        Returns:
            Formatted context string
        """
        results = self.query(question, n_results=n_results)

        if not results:
            return "No relevant context found in zppy knowledge base."

        sections = []
        char_limit = max_tokens * 4  # Rough chars-per-token estimate
        current_chars = 0

        for result in results:
            source_label = result.collection.replace("zppy_", "").replace("_", " ")
            entry = f"[{source_label}] {result.text}"

            if current_chars + len(entry) > char_limit:
                break

            sections.append(entry)
            current_chars += len(entry)

        return "\n\n---\n\n".join(sections)

    def is_indexed(self) -> bool:
        """Check if the vector database has been populated."""
        for col_name in COLLECTION_NAMES:
            try:
                collection = self.client.get_collection(
                    col_name, embedding_function=self.embedding_fn
                )
                if collection.count() > 0:
                    return True
            except Exception:
                continue
        return False

    def get_stats(self) -> Dict[str, int]:
        """Get statistics about indexed content."""
        stats = {}
        for name in COLLECTION_NAMES:
            try:
                collection = self.client.get_collection(
                    name, embedding_function=self.embedding_fn
                )
                stats[name] = collection.count()
            except Exception:
                stats[name] = 0
        return stats
