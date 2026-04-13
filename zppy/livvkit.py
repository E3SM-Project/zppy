import os
from typing import Any, Dict, List

from configobj import ConfigObj

from zppy.bundle import handle_bundles
from zppy.utils import (
    ParameterInferenceType,
    ParameterNotProvidedError,
    add_dependencies,
    check_status,
    get_file_names,
    get_tasks,
    get_years,
    initialize_template,
    make_executable,
    print_url,
    set_value_of_parameter_if_undefined,
    submit_script,
    write_settings_file,
)


# -----------------------------------------------------------------------------
def livvkit(config: ConfigObj, script_dir: str, existing_bundles, job_ids_file):

    template, _ = initialize_template(config, "livvkit.bash")

    # --- List of livvkit tasks ---
    tasks: List[Dict[str, Any]] = get_tasks(config, "livvkit")
    if len(tasks) == 0:
        return existing_bundles

    # --- Generate and submit livvkit scripts ---
    for c in tasks:

        dependencies: List[str] = []

        if "ts_num_years" in c.keys():
            c["ts_num_years"] = int(c["ts_num_years"])
        # Loop over year sets
        year_sets = get_years(c["years"])
        for s in year_sets:
            c["year1"] = s[0]
            c["year2"] = s[1]
            c["ts_num_years"] = s[1] - s[0] + 1
            c["scriptDir"] = script_dir

            # List of dependencies
            determine_and_add_dependencies(c, dependencies, script_dir)
            prefix: str = f"livvkit_{c['year1']:04d}-{c['year2']:04d}"
            c["prefix"] = prefix
            print(prefix)
            bash_file, settings_file, status_file = get_file_names(script_dir, prefix)
            skip: bool = check_status(status_file)
            if skip:
                continue
            # Create script
            with open(bash_file, "w") as f:
                f.write(template.render(**c))
            make_executable(bash_file)
            c["dependencies"] = dependencies
            write_settings_file(settings_file, c, s)

            # Note --export=All is needed to make sure the executable is copied and executed on the nodes.
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
                else:
                    print(f"...adding to bundle '{c['bundle']}'")

            print(f"   environment_commands={c['environment_commands']}")
            print_url(c, "livvkit")

    return existing_bundles


def add_climo_dependency(
    dependencies: List[str],
    scriptDir: str,
    prefix: str,
    sub: str,
    start_yr: int,
    end_yr: int,
    num_years: int,
) -> None:
    y1: int = start_yr
    y2: int = start_yr + num_years - 1
    while y2 <= end_yr:
        dependencies.append(
            os.path.join(scriptDir, f"{prefix}_{sub}_{y1:04d}-{y2:04d}.status")
        )
        y1 += num_years
        y2 += num_years


def determine_and_add_dependencies(
    _c: Dict[str, Any], dependencies: List[str], script_dir: str
) -> None:

    set_value_of_parameter_if_undefined(
        _c,
        "ts_land_subsection",
        "land_monthly",
        ParameterInferenceType.SECTION_INFERENCE,
    )
    add_dependencies(
        dependencies,
        script_dir,
        "ts",
        _c["ts_land_subsection"],
        _c["year1"],
        _c["year2"],
        _c["ts_num_years"],
    )

    climo_subsections: List[str] = []
    if ("climo_subsections" in _c.keys()) and _c["climo_subsections"] != [""]:
        climo_subsections = _c["climo_subsections"]
    elif ("infer_section_parameters" in _c.keys()) and _c["infer_section_parameters"]:
        grids = ["_native"]
        for data_source in ["cmb", "smb", "racmo", "merra2", "ceres", "era5"]:
            if data_source in _c["sets"]:
                if data_source == "racmo" or data_source in ["cmb", "smb"]:
                    for _icesheet in _c["icesheets"].split(","):
                        grids.append(f"_racmo_{_icesheet}")
                elif data_source == "ceres":
                    # CERES grid is the CMIP6 grid, has no grid name in the task
                    grids.append("")
                else:
                    grids.append(f"_{data_source}")
            grids = list(set(grids))
        for _grid in grids:
            climo_subsections.append(f"land_monthly_climo{_grid}")
    else:
        raise ParameterNotProvidedError(
            f"{climo_subsections} was not provided, and inferring is turned off. Turn on inferring by setting infer_section_parameters to True."
        )

    for climo_subsection in climo_subsections:
        add_climo_dependency(
            dependencies,
            script_dir,
            "climo",
            climo_subsection,
            _c["year1"],
            _c["year2"],
            _c["ts_num_years"],
        )
