"""
RAG Indexer for zppy documentation, parameters, and examples.

This module handles indexing zppy content into a vector database
for semantic search and retrieval.
"""

import os
import re
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field


@dataclass
class Document:
    """Represents a document to be indexed."""
    id: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IndexingStats:
    """Statistics from an indexing run."""
    parameters_indexed: int = 0
    examples_indexed: int = 0
    docs_indexed: int = 0
    errors: List[str] = field(default_factory=list)


class ZppyRAGIndexer:
    """
    Indexes zppy content for RAG-based retrieval.

    Indexes three types of content:
    1. Parameter definitions from default.ini
    2. Example configurations from tests/integration/
    3. Documentation from docs/source/

    Usage:
        indexer = ZppyRAGIndexer("/path/to/zppy")
        indexer.index_all()
    """

    def __init__(
        self,
        zppy_root: str,
        db_path: Optional[str] = None,
    ):
        """
        Initialize the RAG indexer.

        Args:
            zppy_root: Path to the zppy repository root
            db_path: Path for the vector database (default: ~/.zppy-ai/vector_db)
        """
        self.zppy_root = Path(zppy_root)
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
                os.makedirs(self.db_path, exist_ok=True)
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

        Severity 4 (Fatal) suppresses ONNX Runtime's Error-level thread-affinity
        warnings that appear on HPC login nodes when pthread_setaffinity_np fails.
        """
        if self._embedding_fn is None:
            import onnxruntime as ort
            ort.set_default_logger_severity(4)
            from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
            self._embedding_fn = ONNXMiniLM_L6_V2()
        return self._embedding_fn

    def index_all(self, force_reindex: bool = False) -> IndexingStats:
        """
        Index all zppy content.

        Args:
            force_reindex: If True, delete existing collections and reindex

        Returns:
            IndexingStats with counts and any errors
        """
        stats = IndexingStats()

        if force_reindex:
            self._clear_collections()

        # Index each content type
        stats.parameters_indexed = self._index_parameters()
        stats.examples_indexed = self._index_examples()
        stats.docs_indexed = self._index_documentation()

        return stats

    def _clear_collections(self):
        """Delete all existing collections."""
        for name in ["zppy_parameters", "zppy_examples", "zppy_docs"]:
            try:
                self.client.delete_collection(name)
            except Exception:
                pass  # Collection doesn't exist

    def _index_parameters(self) -> int:
        """
        Index parameters from default.ini.

        Parses the INI file to extract parameter definitions with their
        comments, types, and default values.

        Returns:
            Number of parameters indexed
        """
        collection = self.client.get_or_create_collection(
            name="zppy_parameters",
            embedding_function=self.embedding_fn,
            metadata={"description": "zppy configuration parameters"},
        )

        ini_path = self.zppy_root / "zppy" / "defaults" / "default.ini"
        if not ini_path.exists():
            return 0

        content = ini_path.read_text()
        documents = self._parse_ini_parameters(content)

        if not documents:
            return 0

        # Add documents; ChromaDB's default embedding function handles vectorization
        texts = [doc.text for doc in documents]
        collection.add(
            documents=texts,
            metadatas=[doc.metadata for doc in documents],
            ids=[doc.id for doc in documents],
        )

        return len(documents)

    def _parse_ini_parameters(self, content: str) -> List[Document]:
        """
        Parse parameters from INI content.

        Extracts parameter definitions along with their preceding comments.
        """
        documents = []
        seen_ids: set = set()
        current_section = "default"
        comment_buffer = []

        for line in content.split('\n'):
            line = line.strip()

            # Track section headers
            if line.startswith('[') and line.endswith(']'):
                current_section = line[1:-1]
                comment_buffer = []
                continue

            # Accumulate comments
            if line.startswith('#'):
                comment_buffer.append(line[1:].strip())
                continue

            # Parse parameter definition
            if '=' in line and not line.startswith('#'):
                match = re.match(r'(\w+)\s*=\s*(.+)', line)
                if match:
                    param_name = match.group(1)
                    param_def = match.group(2)

                    # Extract type and default
                    type_match = re.match(r'(\w+)\(default=([^)]*)\)', param_def)
                    if type_match:
                        param_type = type_match.group(1)
                        default_value = type_match.group(2).strip('"\'')
                    else:
                        param_type = "unknown"
                        default_value = param_def

                    # Build document text
                    comment_text = ' '.join(comment_buffer) if comment_buffer else ''
                    doc_text = (
                        f"Parameter: {param_name}. "
                        f"Section: [{current_section}]. "
                        f"Type: {param_type}. "
                        f"Default: {default_value or 'none'}. "
                        f"Description: {comment_text}"
                    )

                    # Ensure unique ID — [__many__] sections repeat in default.ini
                    base_id = f"param_{current_section}_{param_name}"
                    doc_id = base_id
                    counter = 1
                    while doc_id in seen_ids:
                        counter += 1
                        doc_id = f"{base_id}_{counter}"
                    seen_ids.add(doc_id)

                    documents.append(Document(
                        id=doc_id,
                        text=doc_text,
                        metadata={
                            "parameter": param_name,
                            "section": current_section,
                            "type": param_type,
                            "default": default_value,
                            "description": comment_text,
                            "source": "default.ini"
                        }
                    ))

                comment_buffer = []

        return documents

    def _index_examples(self) -> int:
        """
        Index example configurations from tests/integration/.

        Each config is chunked by section to allow more precise retrieval.

        Returns:
            Number of example chunks indexed
        """
        collection = self.client.get_or_create_collection(
            name="zppy_examples",
            embedding_function=self.embedding_fn,
            metadata={"description": "zppy example configurations"},
        )

        cfg_dir = self.zppy_root / "tests" / "integration"
        if not cfg_dir.exists():
            return 0

        documents = []

        for cfg_file in cfg_dir.glob("*.cfg"):
            try:
                content = cfg_file.read_text()
                docs = self._parse_config_file(cfg_file.name, content)
                documents.extend(docs)
            except Exception as e:
                print(f"Warning: Could not parse {cfg_file}: {e}")

        if not documents:
            return 0

        # Add documents; ChromaDB's default embedding function handles vectorization
        texts = [doc.text for doc in documents]
        collection.add(
            documents=texts,
            metadatas=[doc.metadata for doc in documents],
            ids=[doc.id for doc in documents],
        )

        return len(documents)

    def _parse_config_file(self, filename: str, content: str) -> List[Document]:
        """
        Parse a config file into indexable documents.

        Splits config into sections and creates a document for each,
        plus a document for the entire config.
        """
        documents = []

        # Extract task types present in the config
        task_types = []
        for task in ['climo', 'ts', 'e3sm_diags', 'mpas_analysis',
                     'ilamb', 'tc_analysis', 'global_time_series', 'e3sm_to_cmip']:
            if f'[{task}]' in content:
                task_types.append(task)

        # Determine config purpose from filename
        purpose = self._infer_config_purpose(filename)

        # Index the full config
        full_doc_text = (
            f"Example zppy configuration: {filename}. "
            f"Purpose: {purpose}. "
            f"Tasks: {', '.join(task_types) if task_types else 'none'}. "
            f"Content:\n{content}"
        )

        # Truncate if too long (embedding models have limits)
        if len(full_doc_text) > 8000:
            full_doc_text = full_doc_text[:8000] + "... [truncated]"

        doc_id = f"cfg_{hashlib.md5(filename.encode()).hexdigest()[:8]}"
        documents.append(Document(
            id=doc_id,
            text=full_doc_text,
            metadata={
                "filename": filename,
                "purpose": purpose,
                "task_types": ",".join(task_types),
                "source": "example_config",
                "chunk_type": "full"
            }
        ))

        # Also index individual sections for more precise retrieval
        sections = self._split_config_sections(content)
        for i, section in enumerate(sections):
            if section['name'] == 'default':
                continue  # Skip default section, not very informative

            section_text = (
                f"Config section [{section['name']}] from {filename}. "
                f"Purpose: {purpose}. "
                f"Content:\n{section['content']}"
            )

            documents.append(Document(
                id=f"{doc_id}_section_{i}",
                text=section_text,
                metadata={
                    "filename": filename,
                    "section": section['name'],
                    "purpose": purpose,
                    "source": "example_config",
                    "chunk_type": "section"
                }
            ))

        return documents

    def _split_config_sections(self, content: str) -> List[Dict[str, str]]:
        """Split config content into sections."""
        sections = []
        current_section = None
        current_content = []

        for line in content.split('\n'):
            # Check for section header
            section_match = re.match(r'^\s*\[(\w+)\]', line)
            if section_match:
                # Save previous section
                if current_section:
                    sections.append({
                        'name': current_section,
                        'content': '\n'.join(current_content)
                    })
                current_section = section_match.group(1)
                current_content = [line]
            elif current_section:
                current_content.append(line)

        # Don't forget last section
        if current_section:
            sections.append({
                'name': current_section,
                'content': '\n'.join(current_content)
            })

        return sections

    def _infer_config_purpose(self, filename: str) -> str:
        """Infer the purpose of a config from its filename."""
        filename_lower = filename.lower()

        if 'campaign' in filename_lower:
            if 'water_cycle' in filename_lower:
                return "water cycle campaign analysis"
            elif 'cryosphere' in filename_lower:
                return "cryosphere campaign analysis"
            elif 'high_res' in filename_lower:
                return "high resolution analysis"
            return "campaign configuration"

        if 'bundle' in filename_lower:
            return "job bundling example"

        if 'min_case' in filename_lower:
            if 'e3sm_diags' in filename_lower:
                if 'climo' in filename_lower:
                    return "minimal e3sm_diags with climatology dependency"
                elif 'ts' in filename_lower:
                    return "minimal e3sm_diags with time series dependency"
                elif 'diurnal' in filename_lower:
                    return "diurnal cycle diagnostics"
                elif 'tc_analysis' in filename_lower:
                    return "tropical cyclone analysis"
                return "minimal e3sm_diags configuration"
            elif 'global_time_series' in filename_lower:
                return "global time series plots"
            elif 'mpas' in filename_lower:
                return "MPAS ocean/ice analysis"
            elif 'ilamb' in filename_lower:
                return "ILAMB land model benchmarking"
            return "minimal test case"

        if 'comprehensive' in filename_lower:
            return "comprehensive full analysis"

        if 'defaults' in filename_lower:
            return "testing default parameter values"

        return "general zppy configuration"

    def _index_documentation(self) -> int:
        """
        Index RST documentation files.

        Returns:
            Number of documentation chunks indexed
        """
        collection = self.client.get_or_create_collection(
            name="zppy_docs",
            embedding_function=self.embedding_fn,
            metadata={"description": "zppy documentation"},
        )

        docs_dir = self.zppy_root / "docs" / "source"
        if not docs_dir.exists():
            return 0

        documents = []

        for rst_file in docs_dir.rglob("*.rst"):
            try:
                content = rst_file.read_text()
                docs = self._parse_rst_file(rst_file, content)
                documents.extend(docs)
            except Exception as e:
                print(f"Warning: Could not parse {rst_file}: {e}")

        if not documents:
            return 0

        # Add documents; ChromaDB's default embedding function handles vectorization
        texts = [doc.text for doc in documents]
        collection.add(
            documents=texts,
            metadatas=[doc.metadata for doc in documents],
            ids=[doc.id for doc in documents],
        )

        return len(documents)

    def _parse_rst_file(self, filepath: Path, content: str) -> List[Document]:
        """
        Parse an RST file into indexable chunks.

        Splits on section headers to create meaningful chunks.
        """
        documents = []
        relative_path = filepath.relative_to(self.zppy_root)

        # Split by RST section headers (lines of =, -, or ~)
        sections = re.split(r'\n(?=[^\n]+\n[=\-~]+\n)', content)

        for i, section in enumerate(sections):
            if not section.strip():
                continue

            # Extract section title if present
            title_match = re.match(r'^([^\n]+)\n[=\-~]+', section.strip())
            title = title_match.group(1) if title_match else f"Section {i}"

            # Clean up RST directives for better embedding
            clean_text = self._clean_rst(section)

            if len(clean_text) < 50:  # Skip very short sections
                continue

            doc_text = (
                f"Documentation: {title}. "
                f"File: {relative_path}. "
                f"Content: {clean_text}"
            )

            # Truncate if too long
            if len(doc_text) > 4000:
                doc_text = doc_text[:4000] + "... [truncated]"

            doc_id = f"doc_{hashlib.md5(f'{filepath}_{i}'.encode()).hexdigest()[:8]}"
            documents.append(Document(
                id=doc_id,
                text=doc_text,
                metadata={
                    "title": title,
                    "file": str(relative_path),
                    "source": "documentation"
                }
            ))

        return documents

    def _clean_rst(self, text: str) -> str:
        """Clean RST markup for better embedding."""
        # Remove directive markers
        text = re.sub(r'\.\. \w+::', '', text)
        # Remove code block markers
        text = re.sub(r'```\w*', '', text)
        # Remove inline code backticks (keep content)
        text = re.sub(r'`([^`]+)`', r'\1', text)
        # Remove reference markers
        text = re.sub(r':ref:`([^`]+)`', r'\1', text)
        # Collapse multiple newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def get_stats(self) -> Dict[str, int]:
        """Get statistics about indexed content."""
        stats = {}
        for name in ["zppy_parameters", "zppy_examples", "zppy_docs"]:
            try:
                collection = self.client.get_collection(name)
                stats[name] = collection.count()
            except Exception:
                stats[name] = 0
        return stats
