"""
zppy-ai: AI-powered assistant for zppy configuration and workflow management.

This is a separate entry point from the core 'zppy' command, providing
AI-enhanced features like interactive config generation, RAG-based
parameter lookup, and configuration validation.

Usage:
    zppy-ai index [--zppy-root PATH] [--force]
    zppy-ai query "how to configure climo"
    zppy-ai validate my_config.cfg
    zppy-ai generate
"""

import argparse
import os
import sys


def _get_zppy_root() -> str:
    """Infer zppy repository root from package location."""
    zppy_pkg_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(zppy_pkg_dir)


def cmd_index(args):
    """Index zppy documentation, parameters, and examples for RAG."""
    from zppy.ai_agents.rag.indexer import ZppyRAGIndexer

    zppy_root = args.zppy_root or _get_zppy_root()
    print(f"Indexing zppy content from: {zppy_root}")

    indexer = ZppyRAGIndexer(zppy_root)
    stats = indexer.index_all(force_reindex=args.force)

    print(f"Indexing complete:")
    print(f"  Parameters indexed: {stats.parameters_indexed}")
    print(f"  Examples indexed:   {stats.examples_indexed}")
    print(f"  Docs indexed:       {stats.docs_indexed}")
    if stats.errors:
        print(f"  Errors: {len(stats.errors)}")
        for err in stats.errors:
            print(f"    - {err}")


def cmd_query(args):
    """Query the zppy knowledge base."""
    from zppy.ai_agents.rag.querier import ZppyRAGQuerier

    querier = ZppyRAGQuerier()

    if not querier.is_indexed():
        print("Knowledge base is empty. Run 'zppy-ai index' first.")
        sys.exit(1)

    question = " ".join(args.question)
    results = querier.query(question, n_results=args.n)

    if not results:
        print("No results found.")
        return

    for i, result in enumerate(results, 1):
        source = result.collection.replace("zppy_", "")
        distance = f"{result.distance:.3f}"
        print(f"\n--- Result {i} [{source}] (distance: {distance}) ---")
        print(result.text[:500])
        if len(result.text) > 500:
            print("... [truncated]")


def cmd_validate(args):
    """Validate a zppy configuration file."""
    from zppy.ai_agents.config_agent import ConfigAgent

    agent = ConfigAgent()
    errors = agent.validate_config(args.config)

    if not errors:
        print(f"Validation PASSED: {args.config}")
    else:
        print(f"Validation FAILED: {args.config}")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)


def cmd_generate(args):
    """Generate a zppy configuration interactively (Phase 2)."""
    print("Interactive config generation is not yet implemented.")
    print("This feature will be available in Phase 2.")
    print()
    print("In the meantime, you can:")
    print("  zppy-ai query 'your question'  - Look up parameter docs")
    print("  zppy-ai validate config.cfg     - Validate an existing config")
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        prog="zppy-ai",
        description="AI-powered assistant for zppy configuration and workflow management",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # zppy-ai index
    index_parser = subparsers.add_parser(
        "index", help="Index zppy docs for RAG-based lookup"
    )
    index_parser.add_argument(
        "--zppy-root", help="Path to zppy repository root (auto-detected if omitted)"
    )
    index_parser.add_argument(
        "--force", action="store_true", help="Force re-indexing of all content"
    )

    # zppy-ai query
    query_parser = subparsers.add_parser(
        "query", help="Query the zppy knowledge base"
    )
    query_parser.add_argument("question", nargs="+", help="Question to search for")
    query_parser.add_argument(
        "-n", type=int, default=5, help="Number of results (default: 5)"
    )

    # zppy-ai validate
    validate_parser = subparsers.add_parser(
        "validate", help="Validate a zppy configuration file"
    )
    validate_parser.add_argument("config", help="Path to .cfg file to validate")

    # zppy-ai generate (Phase 2 stub)
    subparsers.add_parser(
        "generate", help="Generate config interactively (coming soon)"
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    commands = {
        "index": cmd_index,
        "query": cmd_query,
        "validate": cmd_validate,
        "generate": cmd_generate,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
