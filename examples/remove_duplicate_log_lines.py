# Written with LivChat
def remove_consecutive_duplicates(input_file_path):
    output_file_path = input_file_path + ".duplicates_removed"
    last_written_line = None

    with (
        open(input_file_path, "r", encoding="utf-8") as infile,
        open(output_file_path, "w", encoding="utf-8") as outfile,
    ):
        for line in infile:
            if line != last_written_line:
                outfile.write(line)
                last_written_line = line
    return output_file_path


if __name__ == "__main__":
    f = "/lcrc/group/e3sm/ac.forsyth2/zppy_pr719_output/unique_id_16/v3.LR.amip_0101/post/scripts/pcmdi_diags_enso_model_vs_obs_2005-2015.o785792"
    remove_consecutive_duplicates(f)
