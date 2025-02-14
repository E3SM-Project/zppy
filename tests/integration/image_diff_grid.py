# Stand-alone python script

import os
from math import ceil

import matplotlib.backends.backend_pdf
import matplotlib.image as mpimg
import matplotlib.pyplot as plt


def make_image_diff_grid(directory):
    files = os.listdir(directory)
    prefixes = [f.split("_diff.png")[0] for f in files if f.endswith("_diff.png")]
    rows = len(prefixes)
    # assert len(files) == 3*rows + 1, f"Expected 3 files per prefix plus grid, got {len(files)} files"
    cols = 3  # actual, expected, diff
    print(f"Constructing a {rows}x{cols} grid of image diffs")
    pdf = matplotlib.backends.backend_pdf.PdfPages(f"{directory}/image_diff_grid.pdf")
    rows_per_page = 4
    num_pages = ceil(rows / rows_per_page)
    for page in range(num_pages):
        fig, axes = plt.subplots(rows_per_page, cols)
        print(f"Page {page}")
        for i, ax_row in enumerate(axes):
            count = page * 3 + i
            if count > len(prefixes) - 1:
                break
            print(f"prefixes[{i}]: {prefixes[count]}")
            if len(prefixes[count]) > 40:
                ax_row[0].set_title(
                    f"{prefixes[count][:40]}...", fontsize=6
                )  # First 40 chars
            else:
                ax_row[0].set_title(prefixes[count], fontsize=6)  # Full title
            img = mpimg.imread(f"{directory}/{prefixes[count]}_actual.png")
            ax_row[0].imshow(img)
            ax_row[0].set_xticks([])
            ax_row[0].set_yticks([])
            img = mpimg.imread(f"{directory}/{prefixes[count]}_expected.png")
            ax_row[1].imshow(img)
            ax_row[1].set_xticks([])
            ax_row[1].set_yticks([])
            img = mpimg.imread(f"{directory}/{prefixes[count]}_diff.png")
            ax_row[2].imshow(img)
            ax_row[2].set_xticks([])
            ax_row[2].set_yticks([])
        fig.tight_layout()
        pdf.savefig(1)
    plt.clf()
    pdf.close()


if __name__ == "__main__":
    path = "/lcrc/group/e3sm/public_html/diagnostic_output/ac.forsyth2/zppy_weekly_comprehensive_v3_www/test_zppy_rc3_unified_rc8/v3.LR.historical_0051/image_check_failures_comprehensive_v3/mpas_analysis/ts_1985-1995_climo_1990-1995/sea_ice/"
    # path = "/lcrc/group/e3sm/public_html//diagnostic_output/ac.forsyth2/zppy_weekly_comprehensive_v3_www/test_zppy_rc3_unified_rc8/v3.LR.historical_0051/image_check_failures_comprehensive_v3/ilamb/_1985-1988/EcosystemandCarbonCycle/EcosystemRespiration/FLUXCOM/"
    make_image_diff_grid(path)
