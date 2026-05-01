"""
zppy-ai: AI-powered assistant for zppy configuration and workflow management.

Usage:
    zppy-ai index [--zppy-root PATH] [--force]
    zppy-ai query "how to configure climo"
    zppy-ai validate my_config.cfg
    zppy-ai ask "what does mapping_file do?"
    zppy-ai configure "run e3sm_diags for my simulation" [--output my.cfg]
    zppy-ai monitor /path/to/scripts [--watch] [--interval 30]
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

    print("Indexing complete:")
    print(f"  Parameters indexed: {stats.parameters_indexed}")
    print(f"  Examples indexed:   {stats.examples_indexed}")
    print(f"  Docs indexed:       {stats.docs_indexed}")
    if stats.errors:
        print(f"  Errors: {len(stats.errors)}")
        for err in stats.errors:
            print(f"    - {err}")


def cmd_query(args):
    """Query the zppy knowledge base (raw vector search, no LLM)."""
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
        print(f"\n--- Result {i} [{source}] (distance: {result.distance:.3f}) ---")
        print(result.text[:500])
        if len(result.text) > 500:
            print("... [truncated]")


def cmd_validate(args):
    """Validate a zppy configuration file against the schema."""
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


def cmd_ask(args):
    """Answer a zppy question using RAG + LLM."""
    from zppy.ai_agents.config_agent import ConfigAgent

    agent = ConfigAgent()

    if not agent.rag_querier.is_indexed():
        print("Knowledge base is empty. Run 'zppy-ai index' first.")
        sys.exit(1)

    question = " ".join(args.question)
    print(agent.ask(question))


def cmd_configure(args):
    """Generate a zppy config from a natural language description."""
    from zppy.ai_agents.config_agent import ConfigAgent

    agent = ConfigAgent()
    description = " ".join(args.description)
    config_text = agent.generate_config(description)

    if args.output:
        with open(args.output, "w") as f:
            f.write(config_text)
        print(f"Config written to: {args.output}")
        print(f"Review and edit, then run: zppy -c {args.output}")
    else:
        print(config_text)


def cmd_monitor(args):
    """Display zppy job statuses from .status files."""
    from zppy.ai_agents.monitor_agent import JobMonitor

    monitor = JobMonitor(args.scripts_dir)

    if args.watch:
        monitor.watch(interval=args.interval)
    else:
        statuses = monitor.get_statuses()
        monitor.display(statuses)
        if statuses:
            print(f"Summary: {monitor.summary(statuses)}")


def cmd_generate(args):
    """Deprecated alias — redirect to configure."""
    print("'generate' has been renamed to 'configure'.")
    print("Run: zppy-ai configure \"<description>\" [--output file.cfg]")
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        prog="zppy-ai",
        description="AI-powered assistant for zppy configuration and workflow management",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # zppy-ai index
    index_parser = subparsers.add_parser(
        "index", help="Index zppy docs, params, and examples for RAG"
    )
    index_parser.add_argument(
        "--zppy-root", help="Path to zppy repository root (auto-detected if omitted)"
    )
    index_parser.add_argument(
        "--force", action="store_true", help="Force re-indexing of all content"
    )

    # zppy-ai query
    query_parser = subparsers.add_parser(
        "query", help="Raw vector search over the knowledge base (no LLM)"
    )
    query_parser.add_argument("question", nargs="+", help="Search terms or question")
    query_parser.add_argument(
        "-n", type=int, default=5, help="Number of results (default: 5)"
    )

    # zppy-ai validate
    validate_parser = subparsers.add_parser(
        "validate", help="Validate a zppy .cfg file against the schema"
    )
    validate_parser.add_argument("config", help="Path to .cfg file")

    # zppy-ai ask
    ask_parser = subparsers.add_parser(
        "ask", help="Answer a zppy question using RAG + LLM"
    )
    ask_parser.add_argument("question", nargs="+", help="Question to answer")

    # zppy-ai configure
    configure_parser = subparsers.add_parser(
        "configure", help="Generate a zppy config from a natural language description"
    )
    configure_parser.add_argument(
        "description", nargs="+", help="What you want to run"
    )
    configure_parser.add_argument(
        "--output", "-o", help="Save config to this file (default: print to stdout)"
    )

    # zppy-ai monitor
    monitor_parser = subparsers.add_parser(
        "monitor", help="Show zppy job statuses from .status files"
    )
    monitor_parser.add_argument(
        "scripts_dir", help="Directory containing zppy .status files"
    )
    monitor_parser.add_argument(
        "--watch", action="store_true", help="Refresh until all jobs finish"
    )
    monitor_parser.add_argument(
        "--interval", type=int, default=30, help="Refresh interval in seconds (default: 30)"
    )

    # zppy-ai generate (deprecated alias)
    subparsers.add_parser("generate", help="Deprecated — use 'configure' instead")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    commands = {
        "index": cmd_index,
        "query": cmd_query,
        "validate": cmd_validate,
        "ask": cmd_ask,
        "configure": cmd_configure,
        "monitor": cmd_monitor,
        "generate": cmd_generate,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
