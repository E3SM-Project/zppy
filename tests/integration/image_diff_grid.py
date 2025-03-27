# Stand-alone python script

import os
from math import ceil

import matplotlib.backends.backend_pdf
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from mache import MachineInfo


def make_image_diff_grid(directory, pdf_name="image_diff_grid.pdf", rows_per_page=5):
    machine_info = MachineInfo(machine=os.environ["E3SMU_MACHINE"])
    web_portal_base_path = machine_info.config.get("web_portal", "base_path")
    web_portal_base_url = machine_info.config.get("web_portal", "base_url")
    print(f"web_portal_base_path: {web_portal_base_path}")
    print(f"web_portal_base_url: {web_portal_base_url}")

    if not directory.startswith(web_portal_base_path):
        print(
            f"Directory {directory} is not a subdir of web portal base path: {web_portal_base_path}"
        )
        return
    pdf_path = f"{directory}/{pdf_name}"
    pdf = matplotlib.backends.backend_pdf.PdfPages(pdf_path)
    print(f"Saving to:\n{pdf_path}")
    subdir = directory.removeprefix(web_portal_base_path)
    print(f"Go to:\n{web_portal_base_url}/{subdir}/{pdf_name}")

    prefixes = []
    # print(f"Walking directory: {directory}")
    for root, _, files in os.walk(directory):
        # print(f"root: {root}")
        for file_name in files:
            # print(f"file_name: {file_name}")
            if file_name.endswith("_diff.png"):
                prefixes.append(f"{root}/{file_name.split('_diff.png')[0]}")
    rows = len(prefixes)
    cols = 3  # actual, expected, diff
    print(f"Constructing a {rows}x{cols} grid of image diffs")

    num_pages = ceil(rows / rows_per_page)
    for page in range(num_pages):
        fig, axes = plt.subplots(rows_per_page, cols)
        print(f"Page {page}")
        for i, ax_row in enumerate(axes):
            count = page * 3 + i
            if count > len(prefixes) - 1:
                break
            # We already know all the files are in `directory`; no need to repeat it.
            short_title = prefixes[count].removeprefix(directory)
            print(f"short_title {i}: {short_title}")
            ax_row[1].set_title(short_title, fontsize=6)
            img = mpimg.imread(f"{prefixes[count]}_actual.png")
            ax_row[0].imshow(img)
            ax_row[0].set_xticks([])
            ax_row[0].set_yticks([])
            img = mpimg.imread(f"{prefixes[count]}_expected.png")
            ax_row[1].imshow(img)
            ax_row[1].set_xticks([])
            ax_row[1].set_yticks([])
            img = mpimg.imread(f"{prefixes[count]}_diff.png")
            ax_row[2].imshow(img)
            ax_row[2].set_xticks([])
            ax_row[2].set_yticks([])
        fig.tight_layout()
        pdf.savefig(1)
        plt.close(fig)
    plt.clf()
    pdf.close()
    print(f"Reminder:\n{web_portal_base_url}/{subdir}/{pdf_name}")


def make_all_grids(username, unique_id):
    # username -- username of who generated the results
    # unique_id -- unique id of the test

    machine_info = MachineInfo(machine=os.environ["E3SMU_MACHINE"])
    web_portal_base_path = machine_info.config.get("web_portal", "base_path")
    v2_path = f"{web_portal_base_path}/{username}/zppy_weekly_comprehensive_v2_www/{unique_id}/v2.LR.historical_0201/image_check_failures_comprehensive_v2"
    v3_path = f"{web_portal_base_path}/{username}/zppy_weekly_comprehensive_v3_www/{unique_id}/v3.LR.historical_0051/image_check_failures_comprehensive_v3"
    bundles_path = f"{web_portal_base_path}/{username}/zppy_weekly_bundles_www/{unique_id}/v3.LR.historical_0051/image_check_failures_bundles"
    paths = [v2_path, v3_path, bundles_path]
    tasks = ["e3sm_diags", "mpas_analysis", "global_time_series", "ilamb"]
    for path in paths:
        for task in tasks:
            full_path = f"{path}/{task}"
            if os.path.isdir(full_path):
                make_image_diff_grid(
                    full_path, pdf_name="image_diff_grid_2rows.pdf", rows_per_page=2
                )


if __name__ == "__main__":
    make_all_grids("ac.forsyth2", "test_unified_rc10_20250220")  # Only 12m15.823s
    # Run with `time python image_diff_grid.py`
