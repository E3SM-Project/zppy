#!/usr/bin/env python3
"""
Agentic AI-powered zppy configuration modifier using ollama.
Allows scientists to request diagnostic configurations using natural language.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


class ZppyConfigAgent:
    """Agent to modify zppy configurations based on natural language queries."""

    def __init__(
        self,
        base_config_path: str,
        available_data_path: str,
        model: str,
        knowledge_base_path: str,
    ):
        """
        Initialize the zppy config agent.

        Args:
            base_config_path: Path to the base zppy configuration file
            available_data_path: Path to simulation output reviewer results
            model: Ollama model to use
            knowledge_base_path: JSON file with topic->variable mappings
        """
        self.model: str = model
        self.base_config: str = self._load_file(base_config_path)
        self.available_data: str = self._load_file(available_data_path)

        # Load or use default knowledge base
        self.knowledge_base: Dict[str, Any]
        if knowledge_base_path and Path(knowledge_base_path).exists():
            with open(knowledge_base_path) as f:
                self.knowledge_base = json.load(f)
        else:
            self.knowledge_base = {}

        # Parse available variables from simulation output
        self.available_vars: Dict[str, List[str]] = self._parse_available_variables()

    # Methods listed in order of first use ####################################

    def _load_file(self, path: str) -> str:
        """Load file content as string."""
        with open(path) as f:
            return f.read()

    def _parse_available_variables(self) -> Dict[str, List[str]]:
        """Parse available variables from simulation output reviewer."""
        vars_by_component: Dict[str, List[str]] = {}
        current_component: Optional[str] = None

        for line in self.available_data.split("\n"):
            # Look for component headers like "component=atm"
            comp_match = re.search(r"component=(\w+)", line)
            if comp_match:
                current_component = comp_match.group(1)
                vars_by_component[current_component] = []

            # Look for variable listings (numbered lines)
            var_match = re.match(r"\s+\d+\.\s+(\w+)", line)
            if var_match and current_component:
                vars_by_component[current_component].append(var_match.group(1))

        return vars_by_component

    def process_query(self, query: str, verbose: bool = False) -> str:
        """
        Process a natural language query and return modified config.

        Args:
            query: User's natural language request
            verbose: Print intermediate steps

        Returns:
            Modified zppy configuration as string
        """
        if verbose:
            print(f"\n{'=' * 70}")
            print(f"Processing query: {query}")
            print(f"{'=' * 70}\n")

        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(query)

        if verbose:
            print("Calling ollama...")

        response = self._call_ollama(user_prompt, system_prompt)

        # Clean up response if model added markdown fences
        if response.startswith("```"):
            lines = response.split("\n")
            # Remove first and last line if they're fence markers
            if lines[0].startswith("```") and lines[-1].startswith("```"):
                response = "\n".join(lines[1:-1])

        return response

    def _build_system_prompt(self) -> str:
        """Build the system prompt with context about zppy configs."""

        # Build a concise summary of available variables
        vars_summary = []
        for comp, vars_list in self.available_vars.items():
            vars_summary.append(
                f"{comp}: {len(vars_list)} variables including {', '.join(vars_list[:10])}"
            )
        vars_text = "\n".join(vars_summary)

        return f"""You are an expert assistant for configuring E3SM post-processing diagnostics using zppy.

ZPPY CONFIGURATION STRUCTURE:
- [default]: Global parameters (case name, paths, partition, walltime)
- [climo]: Climatology generation with subsections for different frequencies/grids
- [ts]: Time series generation with subsections for components (atm, land, ocean, etc.)
- [e3sm_to_cmip]: CMIP variable conversion
- [e3sm_diags]: Atmosphere diagnostics (sets: lat_lon, zonal_mean_xy, polar, cosp_histogram, etc.)
- [mpas_analysis]: Ocean/ice diagnostics
- [global_time_series]: Global time series plots
- [ilamb]: Land model benchmarking

CONFIGURATION PARAMETERS:
- active = True/False: Enable/disable a task
- years = "start:end:interval": Time period (e.g., "1850:2050:20")
- vars = "VAR1,VAR2,...": Comma-separated variable list
- sets = "set1,set2,...": Diagnostic sets to run (for e3sm_diags)
- walltime = "HH:MM:SS": Job walltime
- frequency = "monthly"/"daily"/"diurnal_8xdaily": Data frequency

AVAILABLE SIMULATION DATA:
{vars_text}

SCIENTIFIC TOPIC MAPPINGS:
{json.dumps(self.knowledge_base, indent=2)}

INSTRUCTIONS:
1. Analyze the user's request to identify:
   - Relevant variables (check against available data)
   - Time period (default to full range if not specified)
   - Diagnostics/tasks to enable
   - Components to include (atm, land, ocean, ice, rof)

2. Modify the configuration to fulfill the request:
   - Set active=True for relevant tasks, active=False for irrelevant ones
   - Update variable lists to include only relevant variables
   - Adjust time ranges if specified
   - Update diagnostic sets for e3sm_diags
   - Add comments explaining major changes

3. Preserve configuration format:
   - Keep proper indentation (2 spaces per level)
   - Maintain section hierarchy
   - Keep all required parameters
   - Use proper quoting for strings

4. Return ONLY the modified configuration file as plain text
   - No markdown code fences
   - No explanatory text before or after
   - Just the valid zppy configuration

EXAMPLES OF MODIFICATIONS:
- To focus on precipitation: Keep PRECT, PRECL, PRECC in vars; enable diurnal_cycle
- To focus on carbon: Enable ilamb task, select GPP, NBP, HR, AR variables
- For specific time period: Update years parameter (e.g., "1850:1950:10")
- To disable ocean: Set mpas_analysis active=False"""

    def _build_user_prompt(self, query: str) -> str:
        """Build the user prompt for a specific query."""
        return f"""BASE CONFIGURATION:
{self.base_config}

USER REQUEST: {query}

Please modify the configuration to fulfill this request. Return only the modified zppy configuration file."""

    def _call_ollama(self, prompt: str, system_prompt: str) -> str:
        """Call ollama with the given prompt."""
        try:
            result = subprocess.run(
                ["ollama", "run", self.model],
                input=f"{system_prompt}\n\n{prompt}",
                capture_output=True,
                text=True,
                check=True,
                timeout=120,  # 2 minute timeout
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Error calling ollama: {e}", file=sys.stderr)
            print(f"Stderr: {e.stderr}", file=sys.stderr)
            raise
        except subprocess.TimeoutExpired:
            print("Ollama request timed out", file=sys.stderr)
            raise

    def interactive_mode(self):
        """Run in interactive mode for multiple queries."""
        print("=" * 70)
        print("E3SM zppy Configuration Agent")
        print("=" * 70)
        print(f"Model: {self.model}")
        print(f"Available components: {', '.join(self.available_vars.keys())}")
        print("Type 'quit' to exit, 'help' for example queries\n")

        while True:
            try:
                query = input("Enter your request: ").strip()

                if query.lower() in ("quit", "exit", "q"):
                    print("\nExiting...")
                    break

                if query.lower() == "help":
                    self._print_help()
                    continue

                if not query:
                    continue

                modified_config = self.process_query(query, verbose=True)

                print("\n" + "=" * 70)
                print("MODIFIED CONFIGURATION:")
                print("=" * 70)
                print(modified_config)
                print("=" * 70)

                save = input("\nSave this configuration? (y/n): ").strip().lower()
                if save == "y":
                    filename = input(
                        "Enter filename (default: modified_zppy.cfg): "
                    ).strip()
                    if not filename:
                        filename = "modified_zppy.cfg"

                    with open(filename, "w") as f:
                        f.write(modified_config)
                    print(f"✓ Saved to {filename}")

            except KeyboardInterrupt:
                print("\n\nExiting...")
                break
            except Exception as e:
                print(f"✗ Error: {e}", file=sys.stderr)

    def _print_help(self):
        """Print example queries."""
        print("\n" + "=" * 70)
        print("EXAMPLE QUERIES:")
        print("=" * 70)
        print("• Show me diagnostics relevant to the Amazon dry bias")
        print("• Show me diagnostics relevant to AMOC")
        print("• Show me diagnostics on a hindcast 1850-1950")
        print("• Focus on precipitation and clouds only")
        print("• Disable ocean diagnostics")
        print("• Enable carbon cycle analysis with ILAMB")
        print("• Show aerosol diagnostics for 1980-2000")
        print("• Generate only time series, no climatologies")
        print("=" * 70 + "\n")


def main():
    """CLI entry point."""

    parser = argparse.ArgumentParser(
        description="Modify zppy configurations using natural language",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  %(prog)s base_config.cfg simulation_output.txt

  # Single query
  %(prog)s base_config.cfg simulation_output.txt \\
    --query "show me diagnostics relevant to Amazon dry bias" \\
    --output amazon_config.cfg

  # Use larger model
  %(prog)s base_config.cfg simulation_output.txt \\
    --model llama3.1:70b
        """,
    )

    # Required parameters
    parser.add_argument(
        "base_config",
        help="Path to starting point zppy configuration file (output of `zppy_config_generator.py`)",
    )
    parser.add_argument(
        "available_data",
        help="Path to simulation output reviewer results (output of `simulation_output_reviewer.py`)",
    )
    parser.add_argument(
        "--query", help="Single query to process (otherwise runs interactively)"
    )

    # Optional parameters
    parser.add_argument(
        "--model",
        default="llama3.1:8b",
        help="Ollama model to use (default: llama3.1:8b)",
    )
    parser.add_argument(
        "--knowledge-base",
        default="/home/ac.forsyth2/ez/zppy/config_builder/knowledge_base.json",
        help="JSON file mapping topics to variables",
    )
    parser.add_argument(
        "--output",
        default="tailored_zppy_config.cfg",
        help="Output file for modified config (with --query)",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Print detailed processing steps"
    )

    args = parser.parse_args()

    # Verify ollama is available
    try:
        subprocess.run(["ollama", "list"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: ollama not found. Please install ollama first:", file=sys.stderr)
        print("  https://ollama.ai", file=sys.stderr)
        print(
            "  Official instructions: https://ollama.com/download. For Linux, that shows `curl -fsSL https://ollama.com/install.sh | sh`. After installation, verify that Ollama is available by running `ollama --version`",
            file=sys.stderr,
        )
        sys.exit(1)

    agent = ZppyConfigAgent(
        args.base_config,
        args.available_data,
        model=args.model,
        knowledge_base_path=args.knowledge_base,
    )

    if args.query:
        # Single query mode
        modified_config = agent.process_query(args.query, verbose=args.verbose)

        if args.output:
            with open(args.output, "w") as f:
                f.write(modified_config)
            print(f"✓ Modified configuration saved to {args.output}")
        else:
            print(modified_config)
    else:
        # Interactive mode
        agent.interactive_mode()


if __name__ == "__main__":
    main()
