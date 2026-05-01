"""
Configuration Agent for zppy.

Provides AI-assisted configuration file generation, validation,
and parameter documentation lookup.
"""

import os
from pathlib import Path
from typing import List, Optional

from configobj import ConfigObj
from validate import Validator

_GENERATE_SYSTEM = """\
You are an expert in zppy, the E3SM post-processing toolchain.
Generate a valid zppy .cfg configuration file from the user's requirements.

zppy .cfg files use ConfigObj INI syntax:
- [default] sets global parameters (case, input, output, www, account, partition, walltime, etc.)
- Task sections [climo], [ts], [e3sm_diags], [mpas_analysis], [global_time_series], etc.
  enable specific post-processing tasks
- Subsections use [[name]] for multiple instances of the same task type
- active = True must be set in each task section
- years format: "start:end:chunk",  e.g. "1985:1989:5", processes 1985-1989 in 5-yr chunks
- walltime format: "HH:MM:SS"
- String lists: comma-separated quoted values with trailing comma, e.g. "val1", "val2",
- Boolean values: True or False (capitalised)

Use the provided context (parameters, examples) to set sensible defaults.
Return ONLY the raw .cfg file content — no explanation, no markdown fences.
"""

_ASK_SYSTEM = """\
You are an expert assistant for zppy, the E3SM post-processing toolchain.
Answer questions accurately using the provided context from the zppy knowledge base.
If the context does not contain enough information, say so clearly.
Be concise and practical — users are HPC scientists who want direct answers.
"""


class ConfigAgent:
    """
    AI-powered assistant for zppy configuration.

    Capabilities:
    - Look up parameter documentation via RAG
    - Validate configuration files against the zppy schema
    - Generate configuration files from natural language (Phase 2)

    Usage:
        agent = ConfigAgent()
        errors = agent.validate_config("my_run.cfg")
        help_text = agent.get_parameter_help("mapping_file")
    """

    def __init__(
        self,
        zppy_root: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
    ):
        """
        Initialize the ConfigAgent.

        Args:
            zppy_root: Path to zppy repo root. If None, inferred from package location.
            anthropic_api_key: API key for Claude. If None, reads ANTHROPIC_API_KEY env var.
        """
        if zppy_root is None:
            # Infer from installed package location: zppy/ai_agents/ -> zppy/ -> repo root
            zppy_pkg_dir = Path(__file__).parent.parent
            self.zppy_root = zppy_pkg_dir.parent
            self.zppy_pkg_dir = zppy_pkg_dir
        else:
            self.zppy_root = Path(zppy_root)
            self.zppy_pkg_dir = self.zppy_root / "zppy"

        self.anthropic_api_key = anthropic_api_key or os.environ.get(
            "ANTHROPIC_API_KEY"
        )
        self._defaults_path = self.zppy_pkg_dir / "defaults" / "default.ini"
        self._rag_querier = None
        self._llm_client = None

    @property
    def rag_querier(self):
        """Lazy-initialize the RAG querier."""
        if self._rag_querier is None:
            from zppy.ai_agents.rag.querier import ZppyRAGQuerier

            self._rag_querier = ZppyRAGQuerier()
        return self._rag_querier

    @property
    def llm_client(self):
        """Lazy-initialize the LLM client."""
        if self._llm_client is None:
            from zppy.ai_agents.llm_client import LLMClient

            self._llm_client = LLMClient(api_key=self.anthropic_api_key)
        return self._llm_client

    def _call_llm(self, system: str, user: str, max_tokens: int = 4096) -> str:
        """Delegate to the LLM client. Single place to swap backends."""
        return self.llm_client.call(system=system, user=user, max_tokens=max_tokens)

    def validate_config(self, config_path: str) -> List[str]:
        """
        Validate a zppy configuration file against the schema.

        Uses the same ConfigObj + Validator approach as zppy's core
        validation in __main__.py:_validate_config().

        Args:
            config_path: Path to the .cfg file to validate

        Returns:
            List of validation error messages. Empty list means valid.
        """
        if not os.path.isfile(config_path):
            return [f"Configuration file not found: {config_path}"]

        if not self._defaults_path.exists():
            return [f"Default config spec not found: {self._defaults_path}"]

        errors = []
        try:
            config = ConfigObj(config_path, configspec=str(self._defaults_path))
            validator = Validator()
            result = config.validate(validator, preserve_errors=True)

            if result is not True:
                errors = self._collect_validation_errors(result)
        except Exception as e:
            errors.append(f"Failed to parse configuration: {e}")

        return errors

    def _collect_validation_errors(self, result, prefix="") -> List[str]:
        """Recursively collect validation errors from ConfigObj result."""
        errors = []
        if isinstance(result, dict):
            for key, value in result.items():
                path = f"{prefix}.{key}" if prefix else key
                if value is True:
                    continue
                elif value is False:
                    errors.append(f"Invalid value for parameter: {path}")
                elif isinstance(value, Exception):
                    errors.append(f"Parameter {path}: {value}")
                elif isinstance(value, dict):
                    errors.extend(self._collect_validation_errors(value, prefix=path))
        return errors

    def get_parameter_help(self, param_name: str) -> str:
        """
        Look up documentation for a zppy parameter using RAG.

        Args:
            param_name: Name of the parameter to look up

        Returns:
            Help text for the parameter, or a not-found message
        """
        results = self.rag_querier.query_parameters(param_name, n_results=3)

        if not results:
            return f"No documentation found for parameter '{param_name}'."

        help_sections = []
        for r in results:
            meta = r.metadata
            section = meta.get("section", "unknown")
            param_type = meta.get("type", "unknown")
            default = meta.get("default", "none")
            description = meta.get("description", r.text)

            help_sections.append(
                f"[{section}] {meta.get('parameter', param_name)}\n"
                f"  Type: {param_type}\n"
                f"  Default: {default}\n"
                f"  {description}"
            )

        return "\n\n".join(help_sections)

    def generate_config(self, requirements: str) -> str:
        """
        Generate a zppy configuration file from natural language requirements.

        Retrieves relevant parameter definitions and example configs via RAG,
        then calls the LLM to produce a valid .cfg file.

        Args:
            requirements: Natural language description of desired configuration

        Returns:
            Raw .cfg file content as a string
        """
        context = self.rag_querier.get_context_for_llm(
            requirements, max_tokens=3000, n_results=5
        )
        user_msg = (
            f"<context>\n{context}\n</context>\n\n"
            f"Generate a zppy config for:\n{requirements}"
        )
        return self._call_llm(_GENERATE_SYSTEM, user_msg)

    def ask(self, question: str) -> str:
        """
        Answer a natural language question about zppy using RAG + LLM.

        Args:
            question: Any zppy-related question

        Returns:
            Answer string from the LLM
        """
        context = self.rag_querier.get_context_for_llm(
            question, max_tokens=3000, n_results=5
        )
        user_msg = (
            f"<context>\n{context}\n</context>\n\n"
            f"Question: {question}"
        )
        return self._call_llm(_ASK_SYSTEM, user_msg)
