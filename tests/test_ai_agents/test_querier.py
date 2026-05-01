import os
import tempfile

import pytest

chromadb = pytest.importorskip("chromadb")

from zppy.ai_agents.rag.querier import COLLECTION_NAMES, QueryResult, ZppyRAGQuerier


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary ChromaDB with sample data."""
    db_path = str(tmp_path / "test_vector_db")
    client = chromadb.PersistentClient(path=db_path)

    # Populate zppy_parameters collection with sample data
    params_col = client.get_or_create_collection("zppy_parameters")
    params_col.add(
        documents=[
            "Parameter: years. Section: [default]. Type: string_list. Default: none. "
            "Description: Year ranges to process, e.g. 1:100:10",
            "Parameter: mapping_file. Section: [default]. Type: string. Default: none. "
            "Description: Path to regridding mapping file",
            "Parameter: walltime. Section: [default]. Type: string. Default: 02:00:00. "
            "Description: SLURM job walltime limit",
        ],
        metadatas=[
            {"parameter": "years", "section": "default", "type": "string_list"},
            {"parameter": "mapping_file", "section": "default", "type": "string"},
            {"parameter": "walltime", "section": "default", "type": "string"},
        ],
        ids=["param_default_years", "param_default_mapping_file", "param_default_walltime"],
    )

    # Populate zppy_examples collection
    examples_col = client.get_or_create_collection("zppy_examples")
    examples_col.add(
        documents=[
            "Example zppy configuration: test_min_case_e3sm_diags.cfg. "
            "Purpose: minimal e3sm_diags configuration. "
            "Tasks: climo, e3sm_diags.",
        ],
        metadatas=[
            {"filename": "test_min_case_e3sm_diags.cfg", "purpose": "minimal e3sm_diags"},
        ],
        ids=["cfg_example_1"],
    )

    # Populate zppy_docs collection
    docs_col = client.get_or_create_collection("zppy_docs")
    docs_col.add(
        documents=[
            "Documentation: Getting Started. File: docs/source/getting_started.rst. "
            "Content: zppy uses configuration files to define post-processing workflows.",
        ],
        metadatas=[
            {"title": "Getting Started", "file": "docs/source/getting_started.rst"},
        ],
        ids=["doc_getting_started"],
    )

    return db_path


class TestZppyRAGQuerier:
    def test_init_default_path(self):
        querier = ZppyRAGQuerier()
        expected = os.path.expanduser("~/.zppy-ai/vector_db")
        assert querier.db_path == expected

    def test_init_custom_path(self, tmp_path):
        custom_path = str(tmp_path / "custom_db")
        querier = ZppyRAGQuerier(db_path=custom_path)
        assert querier.db_path == custom_path

    def test_query_all_collections(self, temp_db):
        querier = ZppyRAGQuerier(db_path=temp_db)
        results = querier.query("year ranges", n_results=2)

        assert len(results) > 0
        assert all(isinstance(r, QueryResult) for r in results)
        # Results should be sorted by distance
        distances = [r.distance for r in results]
        assert distances == sorted(distances)

    def test_query_parameters_only(self, temp_db):
        querier = ZppyRAGQuerier(db_path=temp_db)
        results = querier.query_parameters("walltime", n_results=3)

        assert len(results) > 0
        assert all(r.collection == "zppy_parameters" for r in results)

    def test_query_examples_only(self, temp_db):
        querier = ZppyRAGQuerier(db_path=temp_db)
        results = querier.query_examples("e3sm_diags", n_results=2)

        assert len(results) > 0
        assert all(r.collection == "zppy_examples" for r in results)

    def test_query_docs_only(self, temp_db):
        querier = ZppyRAGQuerier(db_path=temp_db)
        results = querier.query_docs("getting started", n_results=2)

        assert len(results) > 0
        assert all(r.collection == "zppy_docs" for r in results)

    def test_query_nonexistent_collection(self, tmp_path):
        """Querying an empty DB should return empty results, not crash."""
        db_path = str(tmp_path / "empty_db")
        querier = ZppyRAGQuerier(db_path=db_path)
        results = querier.query("anything")
        assert results == []

    def test_get_context_for_llm(self, temp_db):
        querier = ZppyRAGQuerier(db_path=temp_db)
        context = querier.get_context_for_llm("year ranges")

        assert isinstance(context, str)
        assert len(context) > 0
        assert "No relevant context" not in context

    def test_get_context_for_llm_empty_db(self, tmp_path):
        db_path = str(tmp_path / "empty_db")
        querier = ZppyRAGQuerier(db_path=db_path)
        context = querier.get_context_for_llm("anything")
        assert context == "No relevant context found in zppy knowledge base."

    def test_is_indexed(self, temp_db):
        querier = ZppyRAGQuerier(db_path=temp_db)
        assert querier.is_indexed() is True

    def test_is_indexed_empty_db(self, tmp_path):
        db_path = str(tmp_path / "empty_db")
        querier = ZppyRAGQuerier(db_path=db_path)
        assert querier.is_indexed() is False

    def test_get_stats(self, temp_db):
        querier = ZppyRAGQuerier(db_path=temp_db)
        stats = querier.get_stats()

        assert stats["zppy_parameters"] == 3
        assert stats["zppy_examples"] == 1
        assert stats["zppy_docs"] == 1
