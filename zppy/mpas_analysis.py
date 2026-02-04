import os
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from configobj import ConfigObj

from zppy.bundle import handle_bundles
from zppy.utils import (
    check_status,
    get_file_names,
    get_tasks,
    get_years,
    initialize_template,
    make_executable,
    print_url,
    submit_script,
    write_settings_file,
)


# -----------------------------------------------------------------------------
def mpas_analysis(config: ConfigObj, script_dir: str, existing_bundles, job_ids_file):

    template, _ = initialize_template(config, "mpas_analysis.bash")

    # --- List of mpas_analysis tasks ---
    tasks: List[Dict[str, Any]] = get_tasks(config, "mpas_analysis")
    if len(tasks) == 0:
        return existing_bundles

    # --- Generate and submit mpas_analysis scripts ---
    # MPAS-Analysis uses a shared output directory, so only a single
    # job should run at once. To gracefully handle this, we make each
    # MPAS-Analysis task dependant on all previous ones. This may not
    # be 100% fool-proof, but should be a reasonable start

    # Dependencies carried over from previous task.
    carried_over_dependencies: List[str] = []

    # Track base output directories for previously defined mpas_analysis subsections.
    prior_subsection_outputs: Dict[str, str] = {}
    # Track year sets for previously defined subsections so later tasks can reference them.
    prior_subsection_year_sets: Dict[str, Dict[str, List[Tuple[int, int]]]] = {}

    for c in tasks:

        dependencies: List[str] = carried_over_dependencies
        set_subdirs(config, c)
        (
            reference_data_path,
            test_data_path,
            reference_subsection,
            test_subsection,
        ) = _resolve_subsection_paths(c, prior_subsection_outputs)
        ts_year_sets, climo_year_sets, enso_year_sets = _resolve_test_year_sets(
            c, test_subsection, prior_subsection_year_sets
        )
        ref_ts_year_sets, ref_climo_year_sets, ref_enso_year_sets = (
            _resolve_reference_year_sets(
                c, reference_subsection, prior_subsection_year_sets, ts_year_sets
            )
        )

        for ts, climo, enso, ctrl_ts, ctrl_climo, ctrl_enso in zip(
            ts_year_sets,
            climo_year_sets,
            enso_year_sets,
            ref_ts_year_sets,
            ref_climo_year_sets,
            ref_enso_year_sets,
        ):
            if _set_run_years(c, ts, climo, enso):
                continue
            identifier, ref_identifier = _set_identifiers(
                c, script_dir, ctrl_ts, ctrl_climo
            )
            _set_run_config_files(
                c, reference_data_path, test_data_path, ref_identifier, identifier
            )
            prefix = _build_prefix(c, ref_identifier, identifier)
            print(prefix)
            bash_file, settings_file, status_file = get_file_names(script_dir, prefix)
            # Check if we can skip because it completed successfully before
            skip: bool = check_status(status_file)
            if skip:
                # Add to the dependency list
                carried_over_dependencies.append(status_file)
                continue
            # Create script
            with open(bash_file, "w") as f:
                f.write(template.render(**c))
            make_executable(bash_file)
            c["dependencies"] = dependencies
            write_settings_file(settings_file, c, ts)
            export = "ALL"
            existing_bundles = handle_bundles(
                c,
                bash_file,
                export,
                dependFiles=dependencies,
                existing_bundles=existing_bundles,
            )
            if not c["dry_run"]:

                if c["bundle"] == "":
                    # Submit job
                    submit_script(
                        bash_file,
                        status_file,
                        export,
                        job_ids_file,
                        dependFiles=dependencies,
                        fail_on_dependency_skip=c["fail_on_dependency_skip"],
                    )

                    # Note that this line should still be executed even if jobid == -1
                    # The later MPAS-Analysis tasks still depend on this task (and thus will also fail).
                    # Add to the dependency list
                    carried_over_dependencies.append(status_file)
                else:
                    print(f"...adding to bundle {c['bundle']}")

            print(f"   environment_commands={c['environment_commands']}")
            print_url(c, "mpas_analysis")

        if c.get("subsection"):
            output_dir = os.path.abspath(
                os.path.expandvars(os.path.expanduser(c["output"]))
            )
            prior_subsection_outputs[c["subsection"]] = output_dir
            prior_subsection_year_sets[c["subsection"]] = {
                "ts": ts_year_sets,
                "climo": climo_year_sets,
                "enso": enso_year_sets,
            }

    return existing_bundles


def _get_identifier(
    *, ts_year1: int, ts_year2: int, climo_year1: int, climo_year2: int
) -> str:
    # Must match identifier in zppy/templates/mpas_analysis.bash
    ts_y1 = f"{ts_year1:04d}"
    ts_y2 = f"{ts_year2:04d}"
    clim_y1 = f"{climo_year1:04d}"
    clim_y2 = f"{climo_year2:04d}"
    return f"ts_{ts_y1}-{ts_y2}_climo_{clim_y1}-{clim_y2}"


def _resolve_subsection_paths(
    c: Dict[str, Any],
    prior_subsection_outputs: Dict[str, str],
) -> Tuple[str, str, str, str]:
    reference_data_path_value = c.get("reference_data_path", "")
    reference_subsection = _parse_subsection_reference(reference_data_path_value)
    reference_data_path = _resolve_subsection_reference(
        reference_data_path_value,
        prior_subsection_outputs,
        "reference_data_path",
    )
    test_data_path_value = c.get("test_data_path", "")
    test_subsection = _parse_subsection_reference(test_data_path_value)
    test_data_path = _resolve_subsection_reference(
        test_data_path_value,
        prior_subsection_outputs,
        "test_data_path",
    )
    c["reference_data_path"] = reference_data_path
    c["test_data_path"] = test_data_path
    return reference_data_path, test_data_path, reference_subsection, test_subsection


def _resolve_test_year_sets(
    c: Dict[str, Any],
    test_subsection: str,
    prior_subsection_year_sets: Dict[str, Dict[str, List[Tuple[int, int]]]],
) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]], List[Tuple[int, int]]]:
    ts_years_value = c.get("ts_years", [""])
    ts_year_sets: List[Tuple[int, int]] = get_years(ts_years_value)
    if (len(ts_year_sets) == 0) and (test_subsection in prior_subsection_year_sets):
        ts_year_sets = prior_subsection_year_sets[test_subsection]["ts"]

    climo_years_value = c.get("climo_years", [""])
    climo_fallback = ts_year_sets
    if test_subsection in prior_subsection_year_sets:
        if len(get_years(climo_years_value)) == 0:
            climo_fallback = prior_subsection_year_sets[test_subsection]["climo"]

    climo_year_sets = _resolve_year_sets(
        climo_years_value,
        fallback=climo_fallback,
        target_len=len(ts_year_sets),
        label="climo_years",
    )

    enso_years_value = c.get("enso_years", [""])
    enso_fallback = ts_year_sets
    if test_subsection in prior_subsection_year_sets:
        if len(get_years(enso_years_value)) == 0:
            enso_fallback = prior_subsection_year_sets[test_subsection]["enso"]

    enso_year_sets = _resolve_year_sets(
        enso_years_value,
        fallback=enso_fallback,
        target_len=len(ts_year_sets),
        label="enso_years",
    )

    return ts_year_sets, climo_year_sets, enso_year_sets


def _resolve_reference_year_sets(
    c: Dict[str, Any],
    reference_subsection: str,
    prior_subsection_year_sets: Dict[str, Dict[str, List[Tuple[int, int]]]],
    ts_year_sets: List[Tuple[int, int]],
) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]], List[Tuple[int, int]]]:
    ref_ts_years_value = c.get("ref_ts_years", [""])
    ref_ts_fallback = ts_year_sets
    if reference_subsection in prior_subsection_year_sets:
        if len(get_years(ref_ts_years_value)) == 0:
            ref_ts_fallback = prior_subsection_year_sets[reference_subsection]["ts"]

    ref_ts_year_sets = _resolve_year_sets(
        ref_ts_years_value,
        fallback=ref_ts_fallback,
        target_len=len(ts_year_sets),
        label="ref_ts_years",
    )

    ref_climo_years_value = c.get("ref_climo_years", [""])
    ref_climo_fallback = ref_ts_year_sets
    if reference_subsection in prior_subsection_year_sets:
        if len(get_years(ref_climo_years_value)) == 0:
            ref_climo_fallback = prior_subsection_year_sets[reference_subsection][
                "climo"
            ]

    ref_climo_year_sets = _resolve_year_sets(
        ref_climo_years_value,
        fallback=ref_climo_fallback,
        target_len=len(ts_year_sets),
        label="ref_climo_years",
    )

    ref_enso_years_value = c.get("ref_enso_years", [""])
    ref_enso_fallback = ref_ts_year_sets
    if reference_subsection in prior_subsection_year_sets:
        if len(get_years(ref_enso_years_value)) == 0:
            ref_enso_fallback = prior_subsection_year_sets[reference_subsection]["enso"]

    ref_enso_year_sets = _resolve_year_sets(
        ref_enso_years_value,
        fallback=ref_enso_fallback,
        target_len=len(ts_year_sets),
        label="ref_enso_years",
    )

    return ref_ts_year_sets, ref_climo_year_sets, ref_enso_year_sets


def _set_run_years(
    c: Dict[str, Any],
    ts: Tuple[int, int],
    climo: Tuple[int, int],
    enso: Tuple[int, int],
) -> bool:
    c["ts_year1"] = ts[0]
    c["ts_year2"] = ts[1]
    if ("last_year" in c.keys()) and (c["ts_year2"] > c["last_year"]):
        return True
    c["climo_year1"] = climo[0]
    c["climo_year2"] = climo[1]
    if ("last_year" in c.keys()) and (c["climo_year2"] > c["last_year"]):
        return True
    c["enso_year1"] = enso[0]
    c["enso_year2"] = enso[1]
    if ("last_year" in c.keys()) and (c["enso_year2"] > c["last_year"]):
        return True
    return False


def _set_identifiers(
    c: Dict[str, Any],
    script_dir: str,
    ctrl_ts: Tuple[int, int],
    ctrl_climo: Tuple[int, int],
) -> Tuple[str, str]:
    c["scriptDir"] = script_dir
    identifier = _get_identifier(
        ts_year1=c["ts_year1"],
        ts_year2=c["ts_year2"],
        climo_year1=c["climo_year1"],
        climo_year2=c["climo_year2"],
    )
    c["identifier"] = identifier

    ref_identifier = _get_identifier(
        ts_year1=ctrl_ts[0],
        ts_year2=ctrl_ts[1],
        climo_year1=ctrl_climo[0],
        climo_year2=ctrl_climo[1],
    )
    c["ref_identifier"] = ref_identifier
    return identifier, ref_identifier


def _set_run_config_files(
    c: Dict[str, Any],
    reference_data_path: str,
    test_data_path: str,
    ref_identifier: str,
    identifier: str,
) -> None:
    c["controlRunConfigFile"] = (
        _resolve_mpas_analysis_config_file(reference_data_path, ref_identifier)
        if reference_data_path
        else ""
    )
    c["mainRunConfigFile"] = (
        _resolve_mpas_analysis_config_file(test_data_path, identifier)
        if test_data_path
        else ""
    )


def _build_prefix(c: Dict[str, Any], ref_identifier: str, identifier: str) -> str:
    prefix_suffix = (
        f"_ts_{c['ts_year1']:04d}-{c['ts_year2']:04d}"
        f"_climo_{c['climo_year1']:04d}-{c['climo_year2']:04d}"
    )

    if c["controlRunConfigFile"] and (ref_identifier != identifier):
        prefix_suffix = f"{prefix_suffix}_vs_ref_{ref_identifier}"
    if c["subsection"]:
        prefix = f"mpas_analysis_{c['subsection']}{prefix_suffix}"
    else:
        prefix = f"mpas_analysis{prefix_suffix}"
    c["prefix"] = prefix
    return prefix


def _resolve_year_sets(
    years_value: Any,
    *,
    fallback: List[Tuple[int, int]],
    target_len: int,
    label: str,
) -> List[Tuple[int, int]]:
    """
    Parse and normalize year sets.

    Behavior:
    - If the parsed year sets are empty, return fallback.
    - If there is a single year set and target_len > 1, replicate to match target_len.
    - If the length is neither 1 nor target_len (and non-empty), raise ValueError.
    """

    parsed = get_years(years_value)
    if len(parsed) == 0:
        return fallback
    if (len(parsed) == 1) and (target_len > 1):
        return parsed * target_len
    if (target_len > 0) and (len(parsed) != target_len):
        raise ValueError(
            f"{label} has {len(parsed)} ranges but expected 1 or {target_len} to match ts_years."
        )
    return parsed


def _resolve_subsection_reference(
    value: str,
    prior_subsection_outputs: Dict[str, str],
    parameter_name: str,
) -> str:
    if not value or not isinstance(value, str):
        return value

    match = re.match(r"^\s*\[\[\s*(.+?)\s*\]\]\s*$", value)
    if not match:
        return value

    subsection = match.group(1).strip()
    if subsection not in prior_subsection_outputs:
        raise ValueError(
            f"{parameter_name} refers to mpas_analysis subsection '{subsection}', "
            "but it has not been defined earlier in [mpas_analysis]."
        )
    return prior_subsection_outputs[subsection]


def _parse_subsection_reference(value: str) -> str:
    if not value or not isinstance(value, str):
        return ""

    match = re.match(r"^\s*\[\[\s*(.+?)\s*\]\]\s*$", value)
    if not match:
        return ""

    return match.group(1).strip()


def _resolve_mpas_analysis_config_file(run_output_dir: str, identifier: str) -> str:
    """
    Resolve the MPAS-Analysis config file path for a prior run.

    The resolved file is expected to be named:
        mpas_analysis_<identifier>.cfg

    with identifier like:
        ts_1850-2014_climo_1985-2014

    The input is expected to be the prior run's zppy output directory, which
    contains a post/ directory.

    Note: We intentionally do not check for filesystem existence here. This allows
    zppy workflows where the referenced MPAS-Analysis run is produced later in the
    same workflow. MPAS-Analysis will raise an error at runtime if the config file
    is missing.
    """

    path = Path(os.path.expandvars(os.path.expanduser(run_output_dir))).resolve()

    file_name = f"mpas_analysis_{identifier}.cfg"

    cfg_dir = path / "post" / "analysis" / "mpas_analysis" / "cfg"
    return str(cfg_dir / file_name)


def set_subdirs(config: ConfigObj, c: Dict[str, Any]) -> None:
    if config["mpas_analysis"]["shortTermArchive"]:
        c["subdir_ocean"] = "/archive/ocn/hist"
        c["subdir_ice"] = "/archive/ice/hist"
    else:
        c["subdir_ocean"] = "/run"
        c["subdir_ice"] = "/run"
