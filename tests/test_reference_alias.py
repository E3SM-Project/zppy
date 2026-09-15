import json
import re
from pathlib import Path
from typing import Dict, List, Set


REFERENCE_ALIAS_PATH = (
    Path(__file__).parents[1]
    / "zppy"
    / "templates"
    / "inclusions"
    / "pcmdi_diags"
    / "reference_alias.json"
)
SPECIAL_ALIASES: Set[str] = {"default", "defaultpi"}


def _canonicalize_source_name(source: str) -> str:
    return re.sub(r"[^a-z0-9]", "", source.lower())


def test_reference_aliases_uniquely_identify_observational_sources() -> None:
    with REFERENCE_ALIAS_PATH.open() as alias_file:
        reference_aliases: Dict[str, Dict[str, str]] = json.load(alias_file)

    empty_aliases: Dict[str, List[str]] = {
        variable: [
            alias for alias, source in variable_aliases.items() if source == ""
        ]
        for variable, variable_aliases in reference_aliases.items()
        if "" in variable_aliases.values()
    }
    sources_by_alias: Dict[str, Set[str]] = {}
    aliases_by_source: Dict[str, Set[str]] = {}
    for variable_aliases in reference_aliases.values():
        for alias, source in variable_aliases.items():
            if alias in SPECIAL_ALIASES or source == "":
                continue

            canonical_source = _canonicalize_source_name(source)
            sources_by_alias.setdefault(alias, set()).add(canonical_source)
            aliases_by_source.setdefault(canonical_source, set()).add(alias)

    reused_aliases = {
        alias: sources
        for alias, sources in sources_by_alias.items()
        if len(sources) > 1
    }
    duplicated_sources = {
        source: aliases
        for source, aliases in aliases_by_source.items()
        if len(aliases) > 1
    }

    assert empty_aliases == {}
    assert reused_aliases == {}
    assert duplicated_sources == {}
