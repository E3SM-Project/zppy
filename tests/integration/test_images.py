import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import redirect_stderr, redirect_stdout
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


def prepare_test_configs(
    expansions: Dict, diff_dir_suffix: str, requested_tasks: List[str]
) -> List[tuple]:
    """Prepare test configurations based on expansions."""
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

    return test_configs


def map_cfg_to_test_name(cfg: str) -> str:
    """Map from weekly_* config names to actual test names."""
    return cfg.replace("weekly_", "")


def order_results(
    test_results_dict: Dict[str, Results],
    test_configs: List[tuple],
    expansions: Dict,
) -> Dict[str, Results]:
    """Reorder results to match the order in expansions."""
    ordered_results_dict: Dict[str, Results] = dict()

    # Get the order from expansions
    cfg_order = [map_cfg_to_test_name(cfg) for cfg in expansions["cfgs_to_run"]]
    task_order = list(expansions["tasks_to_run"])

    for cfg_name in cfg_order:
        # Find the test config that matches this cfg_name
        matching_config = None
        for config in test_configs:
            if config[0] == cfg_name:
                matching_config = config
                break

        if matching_config is None:
            continue

        test_name = matching_config[0]
        # Add results for each task in the order from expansions
        for task in task_order:
            # Look for exact key match: test_name_task
            expected_key = f"{test_name}_{task}"
            if expected_key in test_results_dict:
                ordered_results_dict[expected_key] = test_results_dict[expected_key]

    return ordered_results_dict


def run_test(
    test_name: str,
    case_name: str,
    expansions: Dict,
    diff_dir_suffix: str,
    tasks_to_run: List[str],
) -> tuple[str, Dict[str, Results], str]:
    """Run a single test and return its name, results dict, and captured output."""
    captured_output = StringIO()

    try:
        test_results_dict: Dict[str, Results] = dict()

        # Use context managers for thread-safe redirection
        with redirect_stdout(captured_output), redirect_stderr(captured_output):
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
        log_filename = f"images_logs/test_{test_name}.log"
        os.makedirs(
            "images_logs", exist_ok=True
        )  # Creates directory if it doesn't exist
        with open(log_filename, "w") as f:
            f.write(output)

        return test_name, test_results_dict, output
    except Exception as e:
        output = captured_output.getvalue()
        # Still write the partial output
        log_filename = f"test_{test_name}.log"
        with open(log_filename, "w") as f:
            f.write(output)
        raise e


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
    test_configs = prepare_test_configs(expansions, diff_dir_suffix, requested_tasks)

    try:
        # Run tests in parallel using ProcessPoolExecutor for isolated stdout/stderr
        print(f"Running {len(test_configs)} tests in parallel")
        print("Individual test logs will be written to test_<name>.log files")
        with ProcessPoolExecutor(max_workers=6) as executor:
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

    # Reorder results to match the order in expansions
    ordered_results_dict = order_results(test_results_dict, test_configs, expansions)

    construct_markdown_summary_table(ordered_results_dict, "test_images_summary.md")

    print("\nTest Summary:")
    # Using alignment specifiers:
    print(f"{'Test':<50} {'Total':>10} {'Correct':>10} {'Status':>10}")
    print("-" * 82)

    all_passed = True
    for key, tr in ordered_results_dict.items():
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

    for tr in ordered_results_dict.values():
        assert tr.image_count_total == tr.image_count_correct
