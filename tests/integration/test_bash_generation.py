import os

from tests.integration.utils import get_expansions


def test_bash_generation():
    # cfg is not machine-specific
    assert os.system("zppy -c tests/integration/test_bash_generation.cfg") == 0
    assert os.system("rm test_bash_generation_output/post/scripts/provenance*") == 0
    expected_dir = get_expansions()["expected_dir"]
    assert (
        os.system(
            f"diff -bur -I 'templateDir' test_bash_generation_output/post/scripts {expected_dir}expected_bash_files"
        )
        == 0
    )
    assert os.system("rm -r test_bash_generation_output") == 0
