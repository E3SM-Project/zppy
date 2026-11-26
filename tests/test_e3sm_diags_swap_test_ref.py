"""Check the `swap_test_ref` blocks in the run scripts zppy writes for E3SM Diags."""

import ast
from typing import List, Set

from tests.rendering.scenarios import SCENARIOS_BY_NAME, bash_scripts, render_scenario


def _swap_blocks(source: str) -> List[ast.If]:
    # zppy renders `if {{ swap_test_ref }}:` as `if True:` or `if False:`.
    return [
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.Constant)
        and isinstance(node.test.value, bool)
    ]


def _objects_in(block: ast.If) -> Set[str]:
    return {
        node.value.id
        for node in ast.walk(block)
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
    }


def test_each_swap_block_swaps_a_single_parameter() -> None:
    # Each model-vs-model set builds its own parameter object, and its swap
    # block must swap test and reference on that object alone. A block that
    # also touches another set's parameter (e.g. the core `param`) corrupts
    # that set and leaves its own half-swapped.
    files = render_scenario(SCENARIOS_BY_NAME["comprehensive_chrysalis"])
    failures: List[str] = []
    checked: Set[str] = set()
    for name in bash_scripts(files):
        if not name.startswith("e3sm_diags_"):
            continue
        run_script = name.removesuffix(".bash") + ".py"
        assert run_script in files, f"no run script for {name}"
        for block in _swap_blocks(files[run_script]):
            objects = _objects_in(block)
            checked.update(objects)
            if len(objects) != 1:
                failures.append(
                    f"{run_script}, line {block.lineno}: the swap block "
                    f"swaps attributes of {sorted(objects)}"
                )
    assert not failures, "\n".join(failures)
    # Make sure the scenario still covers the swap blocks this test is about.
    assert {"param", "land_param", "enso_param", "qbo_param"} <= checked
