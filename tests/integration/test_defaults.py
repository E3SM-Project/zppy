import os

from tests.integration.utils import get_expansions


def test_defaults():
    # cfg is not machine-specific
    assert os.system("zppy -c tests/integration/test_defaults.cfg") == 0
    assert os.system("rm test_defaults_output/post/scripts/*.bash") == 0
    assert os.system("rm test_defaults_output/post/scripts/provenance*") == 0
    assert (
        os.system(
            "rm -rf test_defaults_output/post/scripts/global_time_series_0001-0020_dir"
        )
        == 0
    )
    expected_dir = get_expansions()["expected_dir"]
    assert (
        os.system(
            f"diff -bur -I 'templateDir' test_defaults_output/post/scripts {expected_dir}test_defaults_expected_files"
        )
        == 0
    )
    assert os.system("rm -r test_defaults_output") == 0
