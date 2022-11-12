import os
import os.path
from typing import List, Set

import jinja2

from zppy.utils import getTasks, makeExecutable


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

    def render(self, config):

        # Initialize jinja2 template engine
        templateLoader = jinja2.FileSystemLoader(
            searchpath=config["default"]["templateDir"]
        )
        templateEnv = jinja2.Environment(loader=templateLoader)
        template = templateEnv.get_template("bundle.bash")

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
        c["qos"] = self.qos
        c["walltime"] = self.walltime
        c["tasks"] = [os.path.split(t)[-1] for t in self.tasks]

        # Create script
        with open(self.bundle_file, "w") as f:
            f.write(template.render(**c))
        makeExecutable(self.bundle_file)

        return

    def add_task(self, scriptFile, dependFiles):

        # Add tasks and dependencies
        self.tasks.append(scriptFile)
        self.dependencies.update(dependFiles)

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
    def display_dependencies(self):
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
def handle_bundles(c, scriptFile, export, dependFiles=[], existing_bundles=[]):
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
    bundle.add_task(scriptFile, dependFiles)
    if export == "ALL":
        # If one task requires export="ALL", then the bundle script will need it as well
        bundle.export = export

    return existing_bundles


# -----------------------------------------------------------------------------
def predefined_bundles(config, scriptDir, existing_bundles):

    # --- List of tasks ---
    tasks = getTasks(config, "bundle")
    if len(tasks) == 0:
        return existing_bundles

    # --- Create new bundles as needed ---
    for c in tasks:
        if c["subsection"] is not None:
            c["bundle"] = c["subsection"]
            c["scriptDir"] = scriptDir
            bundle = Bundle(c)
            existing_bundles.append(bundle)

    return existing_bundles
