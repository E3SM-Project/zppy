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


if __name__ == "__main__":
    # path = <web_portal_base_path>/<username>/zppy_weekly_<test_name>_www/<UNIQUE_ID>/<test_case>/image_check_failures_<test_name>/<task_name>
    path = ""
    make_image_diff_grid(path)
