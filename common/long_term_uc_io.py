import os
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator, List

from common.constants.countries import set_country_trigram
from common.constants.datatypes import DATATYPE_NAMES
from utils.dir_utils import make_dir, uniformize_path_os


@dataclass
class DtSubfolders:
    demand: str = 'demand'
    res_capa_factors: str = 'res_capa-factors'
    generation_capas: str = 'generation_capas'
    interco_capas: str = 'interco_capas'
    hydro: str = 'hydro'


@dataclass
class DtFilePrefix:
    demand: str = 'demand'
    res_capa_factors: str = 'capa_factor'
    generation_capas: str = 'generation-capa'
    interco_capas: str = 'interco-capas'


@dataclass
class ColumnNames:
    date: str = 'date'
    day: str = 'day'
    week: str = 'week'
    target_year: str = 'year'
    climatic_year: str = 'climatic_year'
    production_type: str = 'production_type'
    value: str = 'value'
    min_value: str = 'min_value'
    max_value: str = 'max_value'
    zone: str = 'zone'
    zone_origin: str = 'zone_origin'
    zone_destination: str = 'zone_destination'


@dataclass
class FilesFormat:
    column_sep: str = ';'
    decimal_sep: str = '.'


@dataclass
class ComplemDataSources:
    from_json_tb_modif: str = 'from_json_tb_modif'
    from_eraa_data: str = 'from_eraa_data'


LT_UC_COMMON_FOLDER = 'long_term_uc/common'
COLUMN_NAMES = ColumnNames()
COMPLEM_DATA_SOURCES = ComplemDataSources()
DATA_FOLDER = 'data'
DATE_FORMAT_FILE = '%Y-%m-%d'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
DATE_FORMAT_PRINT = '%Y/%m/%d'
DT_FILE_PREFIX = DtFilePrefix()
DT_SUBFOLDERS = DtSubfolders()
FILES_FORMAT = FilesFormat()
GEN_CAPA_SUBDT_COLS = ['power_capacity', 'power_capacity_turbine', 'power_capacity_pumping',
                       'power_capacity_injection', 'power_capacity_offtake', 'energy_capacity']
# N.B. min/max hydro levels in a unique file -> share same constants below
HYDRO_FILES = {DATATYPE_NAMES.hydro_ror: 'PECD-hydro-daily-ror-generation.csv',
               DATATYPE_NAMES.hydro_inflows: 'PECD-hydro-weekly-inflows.csv',
               DATATYPE_NAMES.hydro_levels_min: 'PECD-hydro-weekly-reservoir-min-max-levels.csv'}
HYDRO_FILES[DATATYPE_NAMES.hydro_levels_max] = HYDRO_FILES[DATATYPE_NAMES.hydro_levels_min]
HYDRO_KEY_COLUMNS = {DATATYPE_NAMES.hydro_ror:
                         [COLUMN_NAMES.zone, COLUMN_NAMES.day, COLUMN_NAMES.week, COLUMN_NAMES.climatic_year],
                     DATATYPE_NAMES.hydro_inflows: [COLUMN_NAMES.zone, COLUMN_NAMES.week, COLUMN_NAMES.climatic_year],
                     DATATYPE_NAMES.hydro_levels_min: [COLUMN_NAMES.zone, COLUMN_NAMES.week]
                     }
HYDRO_KEY_COLUMNS[DATATYPE_NAMES.hydro_levels_max] = HYDRO_KEY_COLUMNS[DATATYPE_NAMES.hydro_levels_min]
HYDRO_VALUE_COLUMNS = {DATATYPE_NAMES.hydro_ror: [COLUMN_NAMES.value],
                       DATATYPE_NAMES.hydro_inflows:
                           ['cum_inflow_into_reservoirs', 'cum_nat_inflow_into_pump-storage_reservoirs'],
                       DATATYPE_NAMES.hydro_levels_min: [COLUMN_NAMES.min_value, COLUMN_NAMES.max_value]}
HYDRO_VALUE_COLUMNS[DATATYPE_NAMES.hydro_levels_max] = HYDRO_VALUE_COLUMNS[DATATYPE_NAMES.hydro_levels_min]
HYDRO_TS_GRANULARITY = {DATATYPE_NAMES.hydro_ror: 'day',
                        DATATYPE_NAMES.hydro_inflows: 'week',
                        DATATYPE_NAMES.hydro_levels_min: 'week',
                        DATATYPE_NAMES.hydro_levels_max: 'week'}
HYDRO_DEFAULT_VALUES = {DATATYPE_NAMES.hydro_ror: {COLUMN_NAMES.value: 0},
                        DATATYPE_NAMES.hydro_inflows:
                            {'cum_inflow_into_reservoirs': 0, 'cum_nat_inflow_into_pump-storage_reservoirs': 0},
                        # extreme values found in ERAA2023.2 data(over all countries)
                        DATATYPE_NAMES.hydro_levels_min: {COLUMN_NAMES.min_value: 0, COLUMN_NAMES.max_value: 5}
                        }
# method used when resampling from week/day granularity to hourly one -> (uniform) distribution,
# or all at first hourly time-slot of the week/day - and 0 for the rest (typically for constraints
# on min/max reservoir levels)


@dataclass
class ResampleMethods:
    uniform_distrib: str = 'uniform_distrib'
    all_at_first_ts: str = 'all_at_first_ts'


HYDRO_DATA_RESAMPLE_METHODS = {DATATYPE_NAMES.hydro_ror: ResampleMethods.uniform_distrib,
                               DATATYPE_NAMES.hydro_inflows: ResampleMethods.uniform_distrib,
                               DATATYPE_NAMES.hydro_levels_min: ResampleMethods.all_at_first_ts,
                               DATATYPE_NAMES.hydro_levels_max: ResampleMethods.all_at_first_ts}
HYDRO_LEVELS_RESAMPLE_FILLNA_VALS = {COLUMN_NAMES.min_value: 0, COLUMN_NAMES.max_value: 1e10}
INPUT_ERAA_FOLDER = f'{DATA_FOLDER}/ERAA_2023-2'
INPUT_FOLDER = 'input'
INPUT_FUEL_SOURCES_FOLDER = f'{DATA_FOLDER}/fuel_sources'
INPUT_LT_UC_SUBFOLDER = f'{INPUT_FOLDER}/long_term_uc'
INPUT_LT_UC_COUNTRY_SUBFOLDER = f'{INPUT_LT_UC_SUBFOLDER}/countries'
INPUT_FUNC_PARAMS_SUBFOLDER = f'{INPUT_FOLDER}/functional_params'
INPUT_DATA_ANALYSIS_SUBFOLDER = f'{INPUT_LT_UC_SUBFOLDER}/data_analysis'
INTERCO_STR_SEP = '2'
INPUT_CY_STRESS_TEST_SUBFOLDER = 'cy_stress-test'
OUTPUT_FOLDER = 'output'
OUTPUT_FOLDER_LT = f'{OUTPUT_FOLDER}/long_term_uc'
OUTPUT_SUBFOLDER_DATA = 'data'
OUTPUT_SUBFOLDER_FIG = 'figures'
OUTPUT_DATA_ANALYSIS_FOLDER = f'{OUTPUT_FOLDER}/data_analysis'


def check_uc_input_folder_content(all_countries: List[str]):
    uc_countries_folder = uniformize_path_os(path_str=os.path.join(INPUT_LT_UC_SUBFOLDER, 'countries'))
    files = os.listdir(uc_countries_folder)
    gitignore_file = '.gitignore'
    if gitignore_file in files:
        files.remove(gitignore_file)
    allowed_files = set([f'{country}.json' for country in all_countries])
    unknown_files = list(set(files) - allowed_files)
    if len(unknown_files) > 0:
        raise Exception(f'Unknown files in UC input folder {uc_countries_folder}: {unknown_files}. '
                        f'Remove then and re-run')


def get_json_usage_params_file() -> str:
    return uniformize_path_os(path_str=os.path.join(INPUT_FUNC_PARAMS_SUBFOLDER, 'usage_params.json'))


def get_json_fixed_params_file() -> str:
    return uniformize_path_os(path_str=os.path.join(INPUT_LT_UC_SUBFOLDER, 'elec-europe_params_fixed.json'))


def get_json_eraa_avail_values_file() -> str:
    return uniformize_path_os(path_str=os.path.join(INPUT_LT_UC_SUBFOLDER, 'elec-europe_eraa-available-values.json'))


def get_json_params_tb_modif_file() -> str:
    return uniformize_path_os(path_str=os.path.join(INPUT_LT_UC_SUBFOLDER, 'elec-europe_params_to-be-modif.json'))


def get_json_solver_params_file() -> str:
    return uniformize_path_os(path_str=os.path.join(INPUT_LT_UC_SUBFOLDER, 'solver_params.json'))


def get_json_fuel_sources_tb_modif_file() -> str:
    return uniformize_path_os(path_str=os.path.join(INPUT_LT_UC_SUBFOLDER, 'fuel_sources_to-be_modif.json'))


def get_json_params_modif_country_files() -> Iterator[str]:
    return map(
        lambda x: uniformize_path_os(path_str=os.path.join(INPUT_LT_UC_COUNTRY_SUBFOLDER, x)),
        filter(lambda x: x.endswith('.json'),
               os.listdir(INPUT_LT_UC_COUNTRY_SUBFOLDER)))


def get_json_pypsa_static_params_file() -> str:
    return uniformize_path_os(path_str=os.path.join(INPUT_LT_UC_SUBFOLDER, 'pypsa_static_params.json'))


def get_json_data_analysis_params_file() -> str:
    return uniformize_path_os(path_str=os.path.join(INPUT_DATA_ANALYSIS_SUBFOLDER,
                                                    'data-analysis_params_to-be-modif.json'))


def get_json_plot_params_file() -> str:
    return uniformize_path_os(path_str=os.path.join(INPUT_FUNC_PARAMS_SUBFOLDER, 'plot_params.json'))


def get_json_fuel_sources_file() -> str:
    return uniformize_path_os(path_str=os.path.join(INPUT_FUEL_SOURCES_FOLDER, 'params.json'))


def get_network_figure(toy_model_output: bool = False, country: str = None, create_subdir: bool = True,
                       n_bus: int = None) -> str:
    output_folder = set_full_lt_uc_output_folder(folder_type='figures', country=country,
                                                 toy_model_output=toy_model_output)
    if create_subdir:
        make_dir(full_path=output_folder)

    n_bus_suffix = f'_{n_bus}-bus' if n_bus is not None else ''

    return f'{output_folder}/network{n_bus_suffix}.png'


def get_output_file_suffix(country: str, year: int, climatic_year: int = None, start_horizon: datetime = None) -> str:
    cy_suffix = f'_cy{climatic_year}' if climatic_year is not None else ''
    date_suffix = f'_{start_horizon.strftime(DATE_FORMAT_FILE)}' if start_horizon is not None else ''
    return f'{country}_{year}{cy_suffix}{date_suffix}'


def get_output_file_named(name: str, extension: str, output_dir: str, country: str, year: int, climatic_year: int,
                          start_horizon: datetime = None) -> str:
    file_suffix = get_output_file_suffix(country=country, year=year, climatic_year=climatic_year,
                                         start_horizon=start_horizon)
    return f'{output_dir}/{name}_{file_suffix}.{extension}'


def get_figure_file_named(name: str, country: str, year: int, climatic_year: int = None,
                          start_horizon: datetime = None, toy_model_output: bool = False) -> str:
    output_folder = set_full_lt_uc_output_folder(folder_type='figures', country=country,
                                                 toy_model_output=toy_model_output)
    return get_output_file_named(name=name, extension='png', output_dir=output_folder, country=country, year=year,
                                 climatic_year=climatic_year, start_horizon=start_horizon)


@dataclass
class OutputFolderNames:
    data: str = 'data'
    figures: str = 'figures'


@dataclass
class FigNamesPrefix:
    capacity: str = 'capa'
    production: str = 'prod'
    prices: str = 'prices'


def get_output_figure(fig_name: str, country: str, year: int, climatic_year: int = None, start_horizon: datetime = None,
                      toy_model_output: bool = False, create_subdir: bool = True) -> str:
    output_fig_filepath = get_figure_file_named(name=fig_name, country=country, year=year, climatic_year=climatic_year,
                                                start_horizon=start_horizon, toy_model_output=toy_model_output)
    if create_subdir:
        subdir = os.path.split(output_fig_filepath)[0]
        make_dir(full_path=subdir)
    return output_fig_filepath


def set_full_lt_uc_output_folder(folder_type: str = None, country: str = None, toy_model_output: bool = False) -> str:
    subfolder = f'monozone_{set_country_trigram(country=country)}' if toy_model_output else 'multizones_eur'
    folders_tb_join = [OUTPUT_FOLDER_LT, subfolder]
    if folder_type is not None:
        folders_tb_join.append(OUTPUT_SUBFOLDER_DATA if folder_type == OutputFolderNames.data else OUTPUT_SUBFOLDER_FIG)
    return '/'.join(folders_tb_join)


# TODO: merge 2 following functions
def get_csv_file_named(name: str, country: str, year: int, climatic_year: int, start_horizon: datetime,
                       toy_model_output: bool = False, create_subdir: bool = True) -> str:
    output_folder = set_full_lt_uc_output_folder(folder_type='data', country=country, toy_model_output=toy_model_output)
    if create_subdir:
        make_dir(full_path=output_folder)

    return get_output_file_named(name, 'csv', output_folder, country, year, climatic_year, start_horizon)


def get_json_file_named(name: str, country: str, year: int, climatic_year: int, start_horizon: datetime,
                        toy_model_output: bool = False, create_subdir: bool = True) -> str:
    output_folder = set_full_lt_uc_output_folder(folder_type='data', country=country, toy_model_output=toy_model_output)
    if create_subdir:
        make_dir(full_path=output_folder)

    return get_output_file_named(name, 'json', output_folder, country, year, climatic_year, start_horizon)


def get_opt_power_file(country: str, year: int, climatic_year: int, start_horizon: datetime,
                       toy_model_output: bool = False) -> str:
    return get_csv_file_named(name='opt_power', country=country, year=year, climatic_year=climatic_year, 
                              start_horizon=start_horizon, toy_model_output=toy_model_output)


def get_storage_opt_dec_file(country: str, year: int, climatic_year: int, start_horizon: datetime,
                             toy_model_output: bool = False) -> str:
    return get_csv_file_named(name='storage_opt_decisions', country=country, year=year, climatic_year=climatic_year, 
                              start_horizon=start_horizon, toy_model_output=toy_model_output)


def get_link_flow_opt_dec_file(country: str, year: int, climatic_year: int, start_horizon: datetime,
                               toy_model_output: bool= False) -> str:
    return get_csv_file_named(name='link-flow_opt_decisions', country=country, year=year, climatic_year=climatic_year, 
                              start_horizon=start_horizon, toy_model_output=toy_model_output)
    

def get_marginal_prices_file(country: str, year: int, climatic_year: int, start_horizon: datetime,
                             toy_model_output: bool = False) -> str:
    return get_csv_file_named(name='marginal_prices', country=country, year=year, climatic_year=climatic_year, 
                              start_horizon=start_horizon, toy_model_output=toy_model_output)

def get_uc_summary_file(country: str, year: int, climatic_year: int, start_horizon: datetime,
                        toy_model_output: bool = False) -> str:
    return get_json_file_named(name='uc-summary', country=country, year=year, climatic_year=climatic_year,
                               start_horizon=start_horizon, toy_model_output=toy_model_output)
