"""Check the `swap_test_ref` blocks in the `e3sm.py` that E3SM Diags jobs write."""

import ast
import re
from typing import List, Set

from tests.rendering.scenarios import SCENARIOS_BY_NAME, bash_scripts, render_scenario

E3SM_PY_HEREDOC = re.compile(
    r"^cat > e3sm\.py << EOF\n(?P<body>.*?)^EOF$", re.MULTILINE | re.DOTALL
)


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
    for name, text in bash_scripts(files).items():
        if not name.startswith("e3sm_diags_"):
            continue
        match = E3SM_PY_HEREDOC.search(text)
        assert match, f"{name} does not write e3sm.py"
        for block in _swap_blocks(match.group("body")):
            objects = _objects_in(block)
            checked.update(objects)
            if len(objects) != 1:
                failures.append(
                    f"{name}, line {block.lineno} of e3sm.py: the swap block "
                    f"swaps attributes of {sorted(objects)}"
                )
    assert not failures, "\n".join(failures)
    # Make sure the scenario still covers the swap blocks this test is about.
    assert {"param", "land_param", "enso_param", "qbo_param"} <= checked
