from typing import Dict, List, Set

from .simulation_output_reviewer import (
    collapse_year_range,
    get_available_filename_metadata,
    get_h_value_representative_files,
    is_valid_year_range_format,
    parse_filename,
)

# Run with:
# pytest test_*.py


def test_get_h_value_representative_files():
    files: List[str] = [
        "v3.LR.historical_0051.eam.h0.1851-01-01-00000.nc",
        "v3.LR.historical_0051.eam.h0.1852-01-01-00000.nc",
        "v3.LR.historical_0051.eam.h1.1851-01-01-00000.nc",
        "v3.LR.historical_0051.eam.h1.1852-01-01-00000.nc",
        "v3.LR.historical_0051.eam.h2.1851-01-01-00000.nc",
        "v3.LR.historical_0051.eam.h2.1852-01-01-00000.nc",
    ]
    actual = get_h_value_representative_files(files, {"h0", "h1", "h2"})
    expected = {
        "h0": "v3.LR.historical_0051.eam.h0.1851-01-01-00000.nc",
        "h1": "v3.LR.historical_0051.eam.h1.1851-01-01-00000.nc",
        "h2": "v3.LR.historical_0051.eam.h2.1851-01-01-00000.nc",
    }
    assert actual == expected


def test_get_available_filename_metadata():
    files: List[str] = [
        "v3.LR.historical_0051.cpl.hi.1851-01-01-00000.nc",
        "v3.LR.historical_0051.cpl.hi.1852-01-01-00000.nc",
    ]
    actual: Dict[str, Set[str]] = get_available_filename_metadata(files)
    expected: Dict[str, Set[str]] = {
        "versions": {"v3"},
        "resolutions": {"LR"},
        "case_names": {"historical_0051"},
        "components": {"cpl"},
        "h_values": {"hi"},
        "dates": {"1851-01-01-00000", "1852-01-01-00000"},
        "file_extensions": {"nc"},
    }
    assert actual == expected


def test_parse_filename():
    metadata_dict: Dict[str, Set[str]] = {
        "versions": set(),
        "resolutions": set(),
        "case_names": set(),
        "components": set(),
        "h_values": set(),
        "dates": set(),
        "file_extensions": set(),
    }
    parse_filename("v3.LR.historical_0051.eam.h0.1850-01.nc", metadata_dict)
    parse_filename("v3.LR.historical_0051.cpl.hi.1851-01-01-00000.nc", metadata_dict)
    parse_filename(
        "v3.LR.historical_0051.mpassi.hist.am.regionalStatistics.1850.01.nc",
        metadata_dict,
    )
    parse_filename(
        "v3.LR.historical_0051.mpassi.hist.am.timeSeriesStatsMonthly.2050-12-01.nc",
        metadata_dict,
    )
    parse_filename("v3.LR.historical_0051.elm.h0.1850-01.nc", metadata_dict)

    assert metadata_dict["versions"] == {"v3"}
    assert metadata_dict["resolutions"] == {"LR"}
    assert metadata_dict["case_names"] == {"historical_0051"}
    assert metadata_dict["components"] == {"eam", "cpl", "mpassi", "elm"}
    assert metadata_dict["h_values"] == {
        "h0",
        "hi",
        "hist.am.regionalStatistics",
        "hist.am.timeSeriesStatsMonthly",
    }
    assert metadata_dict["dates"] == {"1850-01", "1851-01-01-00000", "2050-12-01"}
    assert metadata_dict["file_extensions"] == {"nc"}


def test_string_split():
    string: str = "v3.LR.historical_0051.cpl.hi.1851-01-01-00000.nc"
    actual: List[str] = string.split(".")
    expected: List[str] = [
        "v3",
        "LR",
        "historical_0051",
        "cpl",
        "hi",
        "1851-01-01-00000",
        "nc",
    ]
    assert actual == expected


def test_is_valid_year_range():
    assert is_valid_year_range_format("1851-01-01-00000") == True
    assert is_valid_year_range_format("1852-01-01-00000") == True
    assert is_valid_year_range_format("2018-01-02-00000") == True
    assert is_valid_year_range_format("1985-03") == True
    assert is_valid_year_range_format("1907-06") == True
    assert is_valid_year_range_format("2007") == True  # Just year

    # Invalid formats
    assert is_valid_year_range_format("") == False
    assert is_valid_year_range_format("85-03") == False  # Year too short
    assert is_valid_year_range_format("abcd-01-01") == False
    assert is_valid_year_range_format("2018/01/02") == False  # Wrong separator
    assert is_valid_year_range_format("0999-01") == False  # Year too small


def test_collapse_year_range():
    year_ranges: Set[str] = {
        "1851-01-01-00000",
        "1852-01-01-00000",
        "2007-01-01-00000",
    }
    actual: List[str] = collapse_year_range(year_ranges)
    expected: List[str] = ["1851-1852", "2007"]
    assert actual == expected

    year_ranges = {"2018-01-02-00000", "1985-03", "1907-06", "1907-05", "1908-01"}
    actual = collapse_year_range(year_ranges)
    expected = ["1907-1908", "1985", "2018"]
    assert actual == expected
