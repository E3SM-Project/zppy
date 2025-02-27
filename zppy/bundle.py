import os
import os.path
from typing import Any, Dict, List, Set

from configobj import ConfigObj

from zppy.utils import get_tasks, initialize_template, make_executable


# -----------------------------------------------------------------------------
# Bundles
class Bundle(object):
    def __init__(self, c):
        # Values are taken from the first task in the bundle OR from the bundle section
        self.bundle_name: str = c["bundle"]
        self.account: str = c["account"]
        self.constraint: str = c["constraint"]
        self.dry_run: bool = c["dry_run"]
        self.debug: bool = c["debug"]
        self.environment_commands: str = c["environment_commands"]
        self.script_dir: str = c["scriptDir"]
        self.nodes: int = c["nodes"]
        self.partition: str = c["partition"]
        self.reservation: str = c["reservation"]
        self.qos: str = c["qos"]
        self.walltime: str = c["walltime"]

        self.bundle_file: str = f"{self.script_dir}/{self.bundle_name}.bash"
        self.bundle_status: str = f"{self.script_dir}/{self.bundle_name}.status"
        self.bundle_output: str = self.bundle_file.strip(".bash") + ".o%j"

        self.tasks: List[str] = []
        self.dependencies: Set[str] = set()
        self.dependencies_internal: Set[str] = set()
        self.dependencies_external: Set[str] = set()

        self.export: str = "NONE"

    def render(self, config) -> None:
        template, _ = initialize_template(config, "bundle.bash")
        # Populate dictionary
        c = {}
        c["machine"] = config["default"]["machine"]
        c["account"] = config["default"]["account"]
        c["constraint"] = self.constraint
        c["debug"] = self.debug
        c["environment_commands"] = self.environment_commands
        c["scriptDir"] = self.script_dir
        c["prefix"] = self.bundle_name
        c["nodes"] = self.nodes
        c["partition"] = self.partition
        c["reservation"] = self.reservation
        c["qos"] = self.qos
        c["walltime"] = self.walltime
        c["tasks"] = [os.path.split(t)[-1] for t in self.tasks]

        # Create script
        with open(self.bundle_file, "w") as f:
            f.write(template.render(**c))
        make_executable(self.bundle_file)

    def add_task(self, script_file, depend_files) -> None:
        # Add tasks and dependencies
        self.tasks.append(script_file)
        self.dependencies.update(depend_files)
        # Sort through dependencies to determine in or out of bundle
        # Remove extensions before performing inclusion test.
        tasks = [os.path.splitext(t)[0] for t in self.tasks]
        for dependency in self.dependencies:
            required = os.path.splitext(dependency)[0]
            if required in tasks:
                self.dependencies_internal.add(dependency)
            else:
                self.dependencies_external.add(dependency)

    # Useful for debugging
    def display_dependencies(self) -> None:
        print(f"Displaying dependencies for {self.bundle_name}")
        print("dependencies_internal:")
        if self.dependencies_internal:
            for dependency in self.dependencies_internal:
                d = os.path.split(dependency)[-1]
                print(f"  {d}")
        else:
            # If we're in this block, then the list is empty.
            print("  None")
        print("dependencies_external:")
        if self.dependencies_external:
            for dependency in self.dependencies_external:
                d = os.path.split(dependency)[-1]
                print(f"  {d}")
        else:
            # If we're in this block, then the list is empty.
            print("  None")


# -----------------------------------------------------------------------------
def handle_bundles(
    c: Dict[str, Any],
    script_file,
    export,
    dependFiles=[],
    existing_bundles: List[Bundle] = [],
) -> List[Bundle]:
    bundle_name = c["bundle"]
    if bundle_name == "":
        return existing_bundles
    for b in existing_bundles:
        if b.bundle_name == bundle_name:
            # This bundle already exists
            bundle = b
            break
    else:
        # If we're in this block, then we did not `break` from the for-loop.
        # So, the bundle does not already exist
        bundle = Bundle(c)
        existing_bundles.append(bundle)
    bundle.add_task(script_file, dependFiles)
    if export == "ALL":
        # If one task requires export="ALL", then the bundle script will need it as well
        bundle.export = export
    return existing_bundles


# -----------------------------------------------------------------------------
def predefined_bundles(
    config: ConfigObj, script_dir: str, existing_bundles: List[Bundle]
) -> List[Bundle]:
    # --- List of tasks ---
    tasks = get_tasks(config, "bundle")
    if len(tasks) == 0:
        return existing_bundles
    # --- Create new bundles as needed ---
    for c in tasks:
        if c["subsection"] is not None:
            c["bundle"] = c["subsection"]
            c["scriptDir"] = script_dir
            bundle = Bundle(c)
            existing_bundles.append(bundle)
    return existing_bundles
