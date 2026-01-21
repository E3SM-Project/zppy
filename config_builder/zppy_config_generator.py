#!/usr/bin/env python3
"""
zppy Configuration Generator

Generates zppy configuration files from simulation metadata.
"""

from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from simulation_output_reviewer import (
    ARCHIVE_DIR,
    DirectoryMetadata,
    get_metadata_by_component,
)
from zppy_config_utils import Dependency, get_case_name, get_machine_specifics

UNIQUE_ID = "run7"
ZPPY_CFG_LOCATION = "/home/ac.forsyth2/ez/datathon/"


class ZppyConfigGenerator:
    def __init__(
        self,
        metadata_dict: Dict[str, Optional[DirectoryMetadata]],
        use_only_standard_vars: bool = False,
    ):
        self.metadata_dict = metadata_dict
        self.use_only_standard_vars: bool = use_only_standard_vars

        machine_specifics: Dict[str, str] = get_machine_specifics()
        self.input_path: str = machine_specifics["input_path"]
        self.output_path: str = machine_specifics["output_path"]
        self.www_path: str = machine_specifics["output_path"]
        self.partition: str = machine_specifics["partition"]
        self.qos: str = machine_specifics["qos"]

        self.case_name = get_case_name(metadata_dict)

        # Trackers of available climo & time-series data
        self.dependency_tracker: Dict[str, Dependency] = {
            "climatology_atm_monthly": None,
            "climatology_atm_monthly_diurnal": None,
            "climatology_lnd_monthly": None,
            "ts_atm_monthly": None,
            "ts_atm_daily": None,
            "ts_land_monthly": None,
            "ts_rof_monthly": None,
            "ts_atm_monthly_glb": None,
            "ts_lnd_monthly_glb": None,
            "e3sm_to_cmip_atm_monthly": None,
            "e3sm_to_cmip_lnd_monthly": None,
            "mpas_analysis": None,
        }

    def generate(self) -> str:
        sections: List[str] = []
        sections.append(self._generate_default_section())

        climo_section = self._generate_climo_section()
        sections.append(climo_section)

        ts_section = self._generate_ts_section()
        sections.append(ts_section)

        if any(self.metadata_dict[k] for k in ("atm", "lnd")):
            sections.append(self._generate_e3sm_to_cmip_section())

        if self.metadata_dict["atm"]:
            sections.append(self._generate_e3sm_diags_section())

        if any(self.metadata_dict[k] for k in ("ocn", "ice")):
            sections.append(self._generate_mpas_analysis_section())

        if any(self.metadata_dict[k] for k in ("atm", "lnd", "ocn")):
            sections.append(self._generate_global_time_series_section())

        if any(self.metadata_dict[k] for k in ("atm", "lnd")):
            sections.append(self._generate_ilamb_section())

        # Skipping these tasks:
        # tc_analysis, because of an issue with using the v3 dataset
        # pcmdi_diags, because it's a beta version

        # Skipping model-vs-model for this initial prototype

        return "\n\n".join(sections)

    def _generate_default_section(self) -> str:
        lines = [
            "[default]",
            f'case = "{self.case_name}"',
            'constraint = ""',
            'dry_run = "False"',
            'environment_commands = "" # Use Unified environment',
            "fail_on_dependency_skip = True",
            "infer_path_parameters = False",
            "infer_section_parameters = False",
            f'input = "{self.input_path}"',
            "input_subdir = archive/atm/hist",
            'mapping_file = "map_ne30pg2_to_cmip6_180x360_aave.20200201.nc"',
            f'output = "{self.output_path}"',
            f'partition = "{self.partition}"',
            f'qos = "{self.qos}"',
            f'www = "{self.www_path}"',
        ]

        return "\n".join(lines)

    def _generate_climo_section(self) -> str:
        atm_h0_var_str: str = self._get_var_str("atm", "h0", set())
        atm_h3_var_str: str = self._get_var_str("atm", "h3", set("PRECT"))
        lnd_h0_var_str: str = self._get_var_str("lnd", "h0", set())
        year_increment: int = 2
        years_str: str = self._get_years_str("atm", year_increment)[0]

        lines: List[str] = [
            "[climo]",
            "active = True",
            'walltime = "00:30:00"',
            f'years = "{years_str}"',
            "",
        ]

        subtask_label: str
        if atm_h0_var_str:
            subtask_label = "atm_monthly_180x360_aave"
            lines.extend(
                [
                    f"  [[ {subtask_label} ]]",
                    '  frequency = "monthly"',
                    '  input_files = "eam.h0"',
                    '  input_subdir = "archive/atm/hist"',
                    f'  vars = "{atm_h0_var_str}"',
                    "",
                ]
            )
            self.dependency_tracker["climatology_atm_monthly"] = Dependency(
                subtask_label, atm_h0_var_str, years_str, year_increment
            )

        if atm_h3_var_str:
            subtask_label = "atm_monthly_diurnal_8xdaily_180x360_aave"
            lines.extend(
                [
                    f"  [[ {subtask_label} ]]" '  frequency = "diurnal_8xdaily"',
                    '  input_files = "eam.h3"',
                    '  input_subdir = "archive/atm/hist"',
                    f'  vars = "{atm_h3_var_str}"',
                    "",
                ]
            )
            self.dependency_tracker["climatology_atm_monthly_diurnal"] = Dependency(
                subtask_label, atm_h3_var_str, years_str, year_increment
            )

        if lnd_h0_var_str:
            subtask_label = "land_monthly_climo"
            lines.extend(
                [
                    f"  [[ {subtask_label} ]]",
                    '  frequency = "monthly"',
                    '  input_files = "elm.h0"',
                    '  input_subdir = "archive/lnd/hist"',
                    '  mapping_file = "map_r05_to_cmip6_180x360_aave.20231110.nc"',
                    f'  vars = "{lnd_h0_var_str}"',
                    "",
                ]
            )
            self.dependency_tracker["climatology_lnd_monthly"] = Dependency(
                subtask_label, lnd_h0_var_str, years_str, year_increment
            )

        return "\n".join(lines)

    def _generate_ts_section(self) -> str:
        atm_h0_standard: Set[str] = set(
            "FSNTOA,FLUT,FSNT,FLNT,FSNS,FLNS,SHFLX,QFLX,TAUX,TAUY,PRECC,PRECL,PRECSC,PRECSL,TS,TREFHT,CLDTOT,CLDHGH,CLDMED,CLDLOW,U,PSL".split(
                ","
            )
        )
        lnd_h0_standard: Set[str] = set(
            "FSH,RH2M,LAISHA,LAISUN,QINTR,QOVER,QRUNOFF,QSOIL,QVEGE,QVEGT,SOILICE,SOILLIQ,SOILWATER_10CM,TSA,TSOI,H2OSNO,TOTLITC,CWDC,SOIL1C,SOIL2C,SOIL3C,SOIL4C,WOOD_HARVESTC,TOTVEGC,NBP,GPP,AR,HR".split(
                ","
            )
        )

        atm_h0_var_str: str = self._get_var_str("atm", "h0", atm_h0_standard)
        atm_h1_var_str: str = self._get_var_str("atm", "h1", set("PRECT"))
        lnd_h0_var_str: str = self._get_var_str("lnd", "h0", lnd_h0_standard)
        rof_h0_var_str: str = self._get_var_str(
            "rof", "h0", set("RIVER_DISCHARGE_OVER_LAND_LIQ")
        )
        lnd_all_found_vars_str: str = self._get_var_str("lnd", "h0", set())
        year_increment: int = 2
        years_str: str = self._get_years_str("atm", year_increment)[0]

        lines: List[str] = [
            "[ts]",
            "active = True",
            'walltime = "00:30:00"',
            f'years = "{years_str}"',
            "",
        ]

        subtask_label: str = ""
        if atm_h0_var_str:
            subtask_label = "atm_monthly_180x360_aave"
            lines.extend(
                [
                    f"  [[ {subtask_label} ]]",
                    '  frequency = "monthly"',
                    '  input_files = "eam.h0"',
                    '  input_subdir = "archive/atm/hist"',
                    f'  vars = "{atm_h0_var_str}"',
                    "",
                ]
            )
            self.dependency_tracker["ts_atm_monthly"] = Dependency(
                subtask_label, atm_h0_var_str, years_str, year_increment
            )

        if atm_h1_var_str:
            subtask_label = "atm_daily_180x360_aave"
            lines.extend(
                [
                    f"  [[ {subtask_label} ]]",
                    '  frequency = "daily"',
                    '  input_files = "eam.h1"',
                    '  input_subdir = "archive/atm/hist"',
                    f'  vars = "{atm_h1_var_str}"',
                    "",
                ]
            )
            self.dependency_tracker["ts_atm_daily"] = Dependency(
                subtask_label, atm_h1_var_str, years_str, year_increment
            )

        if lnd_h0_var_str and ("landfrac" in lnd_h0_var_str):
            subtask_label = "land_monthly"
            lines.extend(
                [
                    f"  [[ {subtask_label} ]]",
                    '  extra_vars = "landfrac"',
                    '  frequency = "monthly"',
                    '  input_files = "elm.h0"',
                    '  input_subdir = "archive/lnd/hist"',
                    f'  vars = "{lnd_h0_var_str}"',
                    "",
                ]
            )
            self.dependency_tracker["ts_land_monthly"] = Dependency(
                subtask_label, lnd_h0_var_str, years_str, year_increment
            )

        if rof_h0_var_str and ("areatotal2" in lnd_h0_var_str):
            subtask_label = "rof_monthly"
            lines.extend(
                [
                    f"  [[ {subtask_label} ]]",
                    '  extra_vars = "areatotal2"',
                    '  frequency = "monthly"',
                    '  input_files = "mosart.h0"',
                    '  input_subdir = "archive/rof/hist"',
                    f'  vars = "{rof_h0_var_str}"',
                    "",
                ]
            )
            self.dependency_tracker["ts_rof_monthly"] = Dependency(
                subtask_label, rof_h0_var_str, years_str, year_increment
            )

        # Use year increments of 5 for global time series
        year_increment = 5
        years_str = self._get_years_str("atm", year_increment)[0]

        if atm_h0_var_str:
            subtask_label = "atm_monthly_glb"
            lines.extend(
                [
                    f"  [[ {subtask_label} ]]",
                    '  frequency = "monthly"',
                    '  input_files = "eam.h0"',
                    '  input_subdir = "archive/atm/hist"',
                    '  mapping_file = "glb"',
                    f'  vars = "{atm_h0_var_str}"',
                    "",
                ]
            )
            self.dependency_tracker["ts_atm_monthly_glb"] = Dependency(
                subtask_label, atm_h0_var_str, years_str, year_increment
            )

        if lnd_all_found_vars_str:
            subtask_label = "lnd_monthly_glb"
            lines.extend(
                [
                    f"  [[ {subtask_label} ]]",
                    '  frequency = "monthly"',
                    '  input_files = "elm.h0"',
                    '  input_subdir = "archive/lnd/hist"',
                    '  mapping_file = "glb"',
                    f'  vars = "{lnd_all_found_vars_str}"',
                    "",
                ]
            )
            self.dependency_tracker["ts_lnd_monthly_glb"] = Dependency(
                subtask_label, lnd_all_found_vars_str, years_str, year_increment
            )

        return "\n".join(lines)

    def _generate_e3sm_to_cmip_section(self) -> str:
        standard_cmip_vars: Set[str] = set(
            "ua, va, ta, wa, zg, hur, tas, ts, psl, ps, sfcWind, huss, pr, prc, prsn, evspsbl, tauu, tauv, hfls, clt, rlus, rsds, rsus, hfss, clivi, clwvi, rlut, rsdt, rsuscs, rsut, rtmt, abs550aer, od550aer, rsdscs, tasmax, tasmin".split(
                ", "
            )
        )
        standard_vars: Set[str] = set(
            "ICEFRAC,LANDFRAC,OCNFRAC,PSL,FSNTC,FSNTOAC,SWCF,LWCF,FLUT,FSNT,FSNTOA,FLNT,FLNTC,FSNS,FLNS,FSNS,SHFLX,QFLX,LHFLX,TAUX,TAUY,PRECC,PRECL,PRECSC,PRECSL,TS,TREFHT,U10,QREFHT,TMQ,CLDTOT,CLDHGH,CLDMED,CLDLOW,FLDS,FSDS,TGCLDIWP,TGCLDCWP,TGCLDLWP,FLNSC,FLUTC,FSDSC,SOLIN,FSNSC,AODABS,AODVIS,AODDUST,AREL,TREFMNAV,TREFMXAV,PS,PHIS,U,V,T,Z3".lower().split(
                ","
            )
        )

        cmip_vars_str: str = self._get_var_str("atm", "h0", standard_cmip_vars)
        vars_str: str = self._get_var_str("atm", "h0", standard_vars)

        lines = [
            "[e3sm_to_cmip]",
            "active = True",
            'frequency = "monthly"',
            'walltime = "00:30:00"',
            "",
        ]

        year_increment: int = 2
        subtask_label: str

        dependency_ts_atm_monthly: Optional[Dependency] = self.dependency_tracker[
            "ts_atm_monthly"
        ]
        if dependency_ts_atm_monthly:
            subtask_label = "atm_monthly_180x360_aave"
            lines.extend(
                [
                    f"  [[{subtask_label}]]",
                    '  cmip_plevdata = "" # TODO: Set this',
                    f'  cmip_vars = "{cmip_vars_str}"',
                    '  input_files = "eam.h0"',
                    f'  ts_num_years = "{dependency_ts_atm_monthly.year_increment}"',
                    f'  ts_subsection = "{dependency_ts_atm_monthly.subtask_label}"',
                    f'  vars = "{vars_str}"',
                    f'  years = "{dependency_ts_atm_monthly.years_str}"',
                    "",
                ]
            )
            self.dependency_tracker["e3sm_to_cmip_atm_monthly"] = Dependency(
                subtask_label,
                vars_str,
                dependency_ts_atm_monthly.years_str,
                year_increment,
            )

        dependency_ts_land_monthly: Optional[Dependency] = self.dependency_tracker[
            "ts_land_monthly"
        ]
        if dependency_ts_land_monthly:
            subtask_label = "land_monthly"
            lines.extend(
                [
                    f"  [[{subtask_label}]]",
                    '  input_files = "elm.h0"',
                    f'  ts_num_years = "{dependency_ts_land_monthly.year_increment}"',
                    f'  ts_subsection = "{dependency_ts_land_monthly.subtask_label}"',
                    f'  years = "{dependency_ts_land_monthly.years_str}"',
                    "",
                ]
            )
            self.dependency_tracker["e3sm_to_cmip_land_monthly"] = Dependency(
                subtask_label,
                vars_str,
                dependency_ts_land_monthly.years_str,
                year_increment,
            )

        return "\n".join(lines)

    def _generate_e3sm_diags_section(self) -> str:
        climo_diurnal_frequency: str = ""
        climo_diurnal_subsection: str = ""
        dependency_climo_atm_monthly_diurnal: Optional[Dependency] = (
            self.dependency_tracker["climatology_atm_monthly_diurnal"]
        )
        if dependency_climo_atm_monthly_diurnal:
            climo_diurnal_frequency = "diurnal_8xdaily"
            climo_diurnal_subsection = (
                dependency_climo_atm_monthly_diurnal.subtask_label
            )

        dependency_ts_atm_daily: Optional[Dependency] = self.dependency_tracker[
            "ts_atm_daily"
        ]
        ts_daily_subsection: str = ""
        if dependency_ts_atm_daily:
            ts_daily_subsection = dependency_ts_atm_daily.subtask_label

        dependency_ts_atm_monthly: Optional[Dependency] = self.dependency_tracker[
            "ts_atm_monthly"
        ]
        ts_subsection: str = ""
        if dependency_ts_atm_monthly:
            ts_subsection = dependency_ts_atm_monthly.subtask_label

        sets_str: str = self._get_e3sm_diags_sets()
        years_str: str
        start_year: str
        end_year: str
        year_increment: int = 2
        years_str, start_year, end_year = self._get_years_str("atm", year_increment)

        return "\n".join(
            [
                "[e3sm_diags]",
                "active = True",
                f'climo_diurnal_frequency = "{climo_diurnal_frequency}"',
                f'climo_diurnal_subsection = "{climo_diurnal_subsection}"',
                'climo_subsection = "atm_monthly_180x360_aave"',
                'grid = "180x360_aave"',
                "multiprocessing = True",
                "num_workers = 8",
                f"ref_final_yr = {end_year}",
                f"ref_start_yr = {start_year}",
                f'ref_years = "{start_year}-{end_year}",',
                f'sets = "{sets_str}",',
                f'short_name= "{self.case_name}"',
                f'ts_daily_subsection = "{ts_daily_subsection}"',
                f"ts_num_years = {year_increment}",
                f'ts_subsection = "{ts_subsection}"',
                f'years = "{years_str}"',
                "# Used for mvo and mvm, if ts_num_years is set",
                'obs_ts = "/lcrc/group/e3sm/diagnostics/observations/Atm/time-series/"',
                "",
                "  [[atm_monthly_180x360_aave]]",
                '  reference_data_path = "/lcrc/group/e3sm/diagnostics/observations/Atm/climatology/"',
                '  dc_obs_climo = "/lcrc/group/e3sm/public_html/e3sm_diags_test_data/unit_test_complete_run/obs/climatology"',
                '  streamflow_obs_ts = "/lcrc/group/e3sm/diagnostics/observations/Atm/time-series/"',
            ]
        )

    def _get_e3sm_diags_sets(self) -> str:
        # Eventually: Add "tc_analysis" back in after empty dat is resolved.
        # Eventually: Add "aerosol_budget" back in once that's working for v3.
        available_sets: List[str] = [
            "lat_lon",
            "zonal_mean_xy",
            "zonal_mean_2d",
            "polar",
            "cosp_histogram",
            "meridional_mean_2d",
            "annual_cycle_zonal_mean",
            "zonal_mean_2d_stratosphere",
            "enso_diags",
            "qbo",
            "diurnal_cycle",
            "streamflow",
            "tropical_subseasonal",
            "aerosol_aeronet",
        ]

        # Removing elements from the complete list allows us to retain the standard order of sets.
        # Using `zppy/e3sm_diags.py` as a guide.
        if not self.dependency_tracker["climatology_atm_monthly_diurnal"]:
            available_sets.remove("diurnal_cycle")
        if not self.dependency_tracker["ts_atm_monthly"]:
            available_sets.remove("enso_diags")
            available_sets.remove("qbo")
        if not self.dependency_tracker["ts_atm_daily"]:
            available_sets.remove("tropical_subseasonal")
        if not self.dependency_tracker["ts_rof_monthly"]:
            available_sets.remove("streamflow")

        return ",".join(available_sets)

    def _generate_mpas_analysis_section(self) -> str:
        year_increment: int = 10

        start_year: str
        end_year: str
        _, start_year, end_year = self._get_years_str("ocn", year_increment)
        if not (start_year and end_year):
            # Use years from ice data as fall-back option
            _, start_year, end_year = self._get_years_str("ice", year_increment)

        climo_years: str = f"{start_year}-{end_year}"
        ts_years: str = f"{start_year}-{end_year}"

        self.dependency_tracker["mpas_analysis"] = Dependency(
            "mpas_analysis", "", year_increment, climo_years, ts_years
        )

        return "\n".join(
            [
                "[mpas_analysis]",
                "active = True",
                f"anomalyRefYear = {start_year}",
                f'climo_years = "{climo_years}",',
                f'enso_years = "{start_year}-{end_year}",',
                'mesh = "IcoswISC30E3r5"',
                "parallelTaskCount = 6",
                "shortTermArchive = True",
                f'ts_years = "{ts_years}",',
            ]
        )

    def _generate_global_time_series_section(self) -> str:
        year_increment: int = 5
        start_year: str
        end_year: str
        _, start_year, end_year = self._get_years_str("atm", year_increment)
        if not (start_year and end_year):
            # Use years from ocn data as fall-back option
            _, start_year, end_year = self._get_years_str("ocn", year_increment)
        if not (start_year and end_year):
            # Use years from lnd data as fall-back option
            _, start_year, end_year = self._get_years_str("lnd", year_increment)

        supported_plots: Set[str] = set()

        dependency_mpas_analysis: Optional[Dependency] = self.dependency_tracker[
            "mpas_analysis"
        ]
        climo_years: str = ""
        ts_years: str = ""
        moc_file_str: str = ""
        if dependency_mpas_analysis:
            climo_years = dependency_mpas_analysis.climo_years
            ts_years = dependency_mpas_analysis.ts_years
            if self.metadata_dict["ocn"]:
                # We need ocn data specifically; ice data only won't work.
                # Handle plots_original:
                # As specified in `zppy_interfaces/global_time_series/utils.py`
                supported_plots.add("change_ohc")
                supported_plots.add("max_moc")
                supported_plots.add("change_sea_level")
                moc_file_str = f"mocTimeSeries_{start_year}-{end_year}.nc"

        dependency_ts_atm_monthly_glb: Optional[Dependency] = self.dependency_tracker[
            "ts_atm_monthly_glb"
        ]
        atm_h0_standard: Set[str] = set()
        plots_atm: str = ""
        if dependency_ts_atm_monthly_glb:
            atm_h0_standard = set("TREFHT".lower().split(","))
            plots_atm = self._get_var_str("atm", "h0", atm_h0_standard)
            # Handle plots_original:
            available_atm_vars: str = self._get_var_str("atm", "h0", set())
            # Set list of variables based on `get_vars_original()` in `zppy_interfaces/global_time_series/coupled_global/utils.py`
            if "restom" in available_atm_vars:
                supported_plots.add("net_toa_flux_restom")
            if ("restom" in available_atm_vars) and ("ressurf" in available_atm_vars):
                supported_plots.add("net_atm_energy_imbalance")
            if "trefht" in available_atm_vars:
                supported_plots.add("global_surface_air_temperature")
            if ("fsntoa" in available_atm_vars) and ("flut" in available_atm_vars):
                supported_plots.add("toa_radiation")
            if (
                ("precc" in available_atm_vars)
                and ("precl" in available_atm_vars)
                and ("qflx" in available_atm_vars)
            ):
                supported_plots.add("net_atm_water_imbalance")

        plots_original: str = ",".join(supported_plots)

        dependency_ts_lnd_monthly_glb: Optional[Dependency] = self.dependency_tracker[
            "ts_lnd_monthly_glb"
        ]
        lnd_h0_standard: Set[str] = set()
        plots_lnd: str = ""
        if dependency_ts_lnd_monthly_glb:
            lnd_h0_standard = set(
                "FSH,RH2M,LAISHA,LAISUN,QINTR,QOVER,QRUNOFF,QSOIL,QVEGE,QVEGT,SOILWATER_10CM,TSA,H2OSNO,TOTLITC,CWDC,SOIL1C,SOIL2C,SOIL3C,SOIL4C,WOOD_HARVESTC,TOTVEGC,NBP,GPP,AR,HR".lower().split(
                    ","
                )
            )
            plots_lnd = self._get_var_str("lnd", "h0", lnd_h0_standard)

        return "\n".join(
            [
                "[global_time_series]",
                "active = True",
                f'climo_years = "{climo_years}",',
                f'experiment_name = "{self.case_name}"',
                f'figstr = "{self.case_name}"',
                f"ts_num_years = {year_increment}",
                f'ts_years = "{ts_years}",',
                f'years = "{start_year}-{end_year}",',
                "",
                "  [[viewer]]",
                "  make_viewer = True",
                f'  plots_atm="{plots_atm}"',
                f'  plots_lnd="{plots_lnd}"',
                f'  plots_original="{plots_original}"',
                f'  moc_file = "{moc_file_str}"',
            ]
        )

    def _generate_ilamb_section(self) -> str:
        year_increment: int = 4

        dependency_ts_atm_monthly: Optional[Dependency] = self.dependency_tracker[
            "ts_atm_monthly"
        ]
        ts_atm_subsection: str = ""
        if dependency_ts_atm_monthly:
            ts_atm_subsection = dependency_ts_atm_monthly.subtask_label
        dependency_ts_land_monthly: Optional[Dependency] = self.dependency_tracker[
            "ts_land_monthly"
        ]
        ts_lnd_subsection: str = ""
        if dependency_ts_land_monthly:
            ts_lnd_subsection = dependency_ts_land_monthly.subtask_label

        dependency_e3sm_to_cmip_atm_monthly: Optional[Dependency] = (
            self.dependency_tracker["e3sm_to_cmip_atm_monthly"]
        )
        e3sm_to_cmip_atm_subsection: str = ""
        if dependency_e3sm_to_cmip_atm_monthly:
            e3sm_to_cmip_atm_subsection = (
                dependency_e3sm_to_cmip_atm_monthly.subtask_label
            )
        dependency_e3sm_to_cmip_lnd_monthly: Optional[Dependency] = (
            self.dependency_tracker["e3sm_to_cmip_lnd_monthly"]
        )
        e3sm_to_cmip_lnd_subsection: str = ""
        if dependency_e3sm_to_cmip_lnd_monthly:
            e3sm_to_cmip_lnd_subsection = (
                dependency_e3sm_to_cmip_lnd_monthly.subtask_label
            )

        start_year: str
        end_year: str
        _, start_year, end_year = self._get_years_str("atm", year_increment)
        if not (start_year and end_year):
            # Use years from lnd data as fall-back option
            _, start_year, end_year = self._get_years_str("lnd", year_increment)

        return "\n".join(
            [
                "[ilamb]",
                "active = True",
                f'e3sm_to_cmip_atm_subsection = "{e3sm_to_cmip_atm_subsection}"',
                f'e3sm_to_cmip_land_subsection = "{e3sm_to_cmip_lnd_subsection}"',
                'ilamb_obs = "/lcrc/group/e3sm/diagnostics/ilamb_data"',
                "nodes = 8",
                f'short_name = "{self.case_name}"',
                f'ts_atm_subsection = "{ts_atm_subsection}"',
                f'ts_land_subsection = "{ts_lnd_subsection}"',
                f"ts_num_years = {year_increment}",
                f'years = "{start_year}:{end_year}:{year_increment}"',
            ]
        )

    def _get_var_str(
        self, component: str, h_value: str, standard_vars: Set[str]
    ) -> str:
        component_h_var_str: str = ""

        component_metadata: Optional[DirectoryMetadata] = self.metadata_dict[component]
        if component_metadata:
            vars_by_h_value: Dict[str, List[str]] = (
                component_metadata.variables_by_h_value
            )
            if h_value in vars_by_h_value.keys():
                component_h_vars = set(vars_by_h_value[h_value])
                if self.use_only_standard_vars and standard_vars:
                    found_vars: Set[str] = component_h_vars & standard_vars
                    component_h_var_str = ",".join(found_vars)
                else:
                    # Use ALL found h# variables
                    # (If `standard_vars=""`, the default is to use all available variables)
                    component_h_var_str = ",".join(component_h_vars)
        return component_h_var_str

    def _get_years_str(
        self, component: str, year_increment: int
    ) -> Tuple[str, str, str]:
        component_metadata: Optional[DirectoryMetadata] = self.metadata_dict[component]
        if component_metadata:
            if component_metadata.year_ranges:
                n: int = len(component_metadata.year_ranges)
                if n > 1:
                    print(f"Warning: Found {n} year ranges for component {component}")
                year_range: str = component_metadata.year_ranges[0]
                if "-" in year_range:
                    parts = year_range.split("-")
                    start_year: str = parts[0]
                    end_year: str = parts[1]
                    return (
                        f"{start_year}:{end_year}:{year_increment}",
                        start_year,
                        end_year,
                    )
        return "", "", ""


def main(verbose: bool = False):
    print(f"Gathering metadata from input path={ARCHIVE_DIR}")
    metadata: Dict[str, DirectoryMetadata] = get_metadata_by_component(ARCHIVE_DIR)

    # Filter out None values
    metadata = {k: v for k, v in metadata.items() if v is not None}
    if not metadata:
        print("ERROR: No metadata found. Check ARCHIVE_DIR path.")
        return

    # Create generator
    generator = ZppyConfigGenerator(metadata, verbose)

    # Generate config
    print("Generating zppy configuration...")
    config = generator.generate()

    # Write to output file
    output_file = Path(f"{ZPPY_CFG_LOCATION}zppy_config_{UNIQUE_ID}.cfg")
    with open(output_file, "w") as f:
        f.write(config)

    print(f"Configuration written to: {output_file.absolute()}")
    print(f"Generated sections for components: {', '.join(metadata.keys())}")


if __name__ == "__main__":
    # Eventually: we could add a zppy command-line flag `--build` that will simply generate a cfg,
    # by calling this script.
    # (Note we should never have zppy automatically run that generated cfg,
    # because it should always be checked by a human first).
    main(True)
