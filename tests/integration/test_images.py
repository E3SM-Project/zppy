import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import StringIO
from typing import Dict, List

from tests.integration.image_checker import (
    Results,
    construct_markdown_summary_table,
    set_up_and_run_image_checker,
)
from tests.integration.utils import get_expansions

V3_CASE_NAME = "v3.LR.historical_0051"
V2_CASE_NAME = "v2.LR.historical_0201"


def intersect_tasks(
    available_tasks: List[str], requested_tasks: List[str]
) -> List[str]:
    return [task for task in requested_tasks if task in available_tasks]


def run_test(
    test_name: str,
    case_name: str,
    expansions: Dict,
    diff_dir_suffix: str,
    tasks_to_run: List[str],
) -> tuple[str, Dict[str, Results], str]:
    """Run a single test and return its name, results dict, and captured output."""
    # Capture both stdout and stderr for this test
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = sys.stderr = captured_output = StringIO()

    try:
        test_results_dict: Dict[str, Results] = dict()
        set_up_and_run_image_checker(
            test_name,
            case_name,
            expansions,
            diff_dir_suffix,
            tasks_to_run,
            test_results_dict,
        )
        output = captured_output.getvalue()

        # Write to individual log file
        log_filename = f"test_{test_name}.log"
        with open(log_filename, "w") as f:
            f.write(output)

        return test_name, test_results_dict, output
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr


def test_images():
    # To test a different branch, set this to True, and manually set the expansions.
    TEST_DIFFERENT_EXPANSIONS = False
    if TEST_DIFFERENT_EXPANSIONS:
        expansions = dict()
        # Example settings:
        expansions["expected_dir"] = "/lcrc/group/e3sm/public_html/zppy_test_resources/"
        expansions["user_www"] = (
            "/lcrc/group/e3sm/public_html/diagnostic_output/ac.forsyth2/"
        )
        expansions["unique_id"] = "test_zppy_20250401"
        diff_dir_suffix = "_test_pr699_try6"
    else:
        expansions = get_expansions()
        diff_dir_suffix = ""

    test_results_dict: Dict[str, Results] = dict()
    requested_tasks: List[str] = list(expansions["tasks_to_run"])

    # Prepare test configurations
    test_configs = []

    # Weekly comprehensive tests
    print("Preparing weekly cfg tests")
    if "weekly_comprehensive_v2" in expansions["cfgs_to_run"]:
        available_tasks = ["e3sm_diags", "mpas_analysis", "global_time_series", "ilamb"]
        tasks_to_run = intersect_tasks(available_tasks, requested_tasks)
        test_configs.append(
            (
                "comprehensive_v2",
                V2_CASE_NAME,
                expansions,
                diff_dir_suffix,
                tasks_to_run,
            )
        )

    if "weekly_comprehensive_v3" in expansions["cfgs_to_run"]:
        # Adds pcmdi_diags
        available_tasks = [
            "e3sm_diags",
            "mpas_analysis",
            "global_time_series",
            "ilamb",
            "pcmdi_diags",
        ]
        tasks_to_run = intersect_tasks(available_tasks, requested_tasks)
        test_configs.append(
            (
                "comprehensive_v3",
                V3_CASE_NAME,
                expansions,
                diff_dir_suffix,
                tasks_to_run,
            )
        )

    if "weekly_bundles" in expansions["cfgs_to_run"]:
        # No mpas_analysis
        available_tasks = ["e3sm_diags", "global_time_series", "ilamb"]
        tasks_to_run = intersect_tasks(available_tasks, requested_tasks)
        test_configs.append(
            (
                "bundles",
                V3_CASE_NAME,
                expansions,
                diff_dir_suffix,
                tasks_to_run,
            )
        )

    # Legacy comprehensive tests
    print("Preparing legacy cfg tests")
    if "weekly_legacy_3.0.0_comprehensive_v2" in expansions["cfgs_to_run"]:
        available_tasks = ["e3sm_diags", "mpas_analysis", "global_time_series", "ilamb"]
        tasks_to_run = intersect_tasks(available_tasks, requested_tasks)
        test_configs.append(
            (
                "legacy_3.0.0_comprehensive_v2",
                V2_CASE_NAME,
                expansions,
                diff_dir_suffix,
                tasks_to_run,
            )
        )

    if "weekly_legacy_3.0.0_comprehensive_v3" in expansions["cfgs_to_run"]:
        available_tasks = ["e3sm_diags", "mpas_analysis", "global_time_series", "ilamb"]
        tasks_to_run = intersect_tasks(available_tasks, requested_tasks)
        test_configs.append(
            (
                "legacy_3.0.0_comprehensive_v3",
                V3_CASE_NAME,
                expansions,
                diff_dir_suffix,
                tasks_to_run,
            )
        )

    if "weekly_legacy_3.0.0_bundles" in expansions["cfgs_to_run"]:
        # No mpas_analysis
        available_tasks = ["e3sm_diags", "global_time_series", "ilamb"]
        tasks_to_run = intersect_tasks(available_tasks, requested_tasks)
        test_configs.append(
            (
                "legacy_3.0.0_bundles",
                V3_CASE_NAME,
                expansions,
                diff_dir_suffix,
                tasks_to_run,
            )
        )

    try:
        # Run tests in parallel
        print(f"Running {len(test_configs)} tests in parallel")
        print("Individual test logs will be written to test_<name>.log files")
        """
        Note from Claude: used ThreadPoolExecutor instead of ProcessPoolExecutor because:
        - Threads share memory, making it easier to work with the shared expansions dict
        - If set_up_and_run_image_checker is I/O bound (file operations, network), threads will be efficient
        - If it's CPU-bound, you could switch to ProcessPoolExecutor for better parallelism
        """
        with ThreadPoolExecutor(max_workers=6) as executor:
            # Submit all tests
            future_to_test = {
                executor.submit(run_test, *config): config[0] for config in test_configs
            }

            # Collect results as they complete
            for future in as_completed(future_to_test):
                test_name = future_to_test[future]
                try:
                    result_name, results_dict, output = future.result()
                    # Merge all results from this test into the main dict
                    test_results_dict.update(results_dict)
                    print(
                        f"✓ Completed: {test_name} ({len(results_dict)} tasks) (log: test_{test_name}.log)"
                    )
                except Exception as e:
                    print(f"✗ Test {test_name} generated an exception: {e}")
                    # Still try to write partial results
                    construct_markdown_summary_table(
                        test_results_dict, "early_test_images_summary.md"
                    )
                    raise e

    except Exception as e:
        construct_markdown_summary_table(
            test_results_dict, "early_test_images_summary.md"
        )
        raise e

    construct_markdown_summary_table(test_results_dict, "test_images_summary.md")

    print("\nTest Summary:")
    print("{'Test':<50} {'Total':>10} {'Correct':>10} {'Status':>10}")
    print("-" * 82)

    all_passed = True
    for key, tr in test_results_dict.items():
        status = (
            "✓ PASS" if tr.image_count_total == tr.image_count_correct else "✗ FAIL"
        )
        if tr.image_count_total != tr.image_count_correct:
            all_passed = False
        print(
            f"{key:<50} {tr.image_count_total:>10} {tr.image_count_correct:>10} {status:>10}"
        )

    print("-" * 82)

    if not all_passed:
        print(
            "\n⚠ Some tests had mismatched or missing images. Check individual log files for details."
        )

    for tr in test_results_dict.values():
        assert tr.image_count_total == tr.image_count_correct
