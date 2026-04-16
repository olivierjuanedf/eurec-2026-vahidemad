import os
from copy import deepcopy
from dataclasses import dataclass
import logging
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from common.constants.aggreg_operations import AggregOpeNames
from common.constants.countries import set_country_trigram
from common.constants.datatypes import DATATYPE_NAMES
from common.constants.eraa_data import ERAAParamNames
from common.constants.prod_types import ProdTypeNames, set_gen_unit_name
from common.constants.pypsa_params import GEN_UNITS_PYPSA_PARAMS, GenUnitsCustomParams
from common.error_msgs import print_errors_list
from common.long_term_uc_io import COLUMN_NAMES, DT_FILE_PREFIX, DT_SUBFOLDERS, FILES_FORMAT, \
    GEN_CAPA_SUBDT_COLS, INPUT_CY_STRESS_TEST_SUBFOLDER, INPUT_ERAA_FOLDER, HYDRO_KEY_COLUMNS, \
    HYDRO_VALUE_COLUMNS, HYDRO_TS_GRANULARITY, HYDRO_DATA_RESAMPLE_METHODS, HYDRO_LEVELS_RESAMPLE_FILLNA_VALS
from common.uc_run_params import UCRunParams
from include.dataset_builder import GenerationUnitData, select_gen_units_data
from utils.basic_utils import get_intersection_of_lists
from utils.df_utils import create_dict_from_cols_in_df, selec_in_df_based_on_list, set_aggreg_col_based_on_corresp, \
    create_dict_from_df_row, resample_and_distribute
from utils.dir_utils import uniformize_path_os
from utils.eraa_data_reader import filter_input_data, gen_capa_pt_str_sanitizer, select_interco_capas, \
    set_aggreg_cf_prod_types_data, read_and_process_hydro_data
from utils.write import json_dump

N_SPACES_MSG = 2
PROD_TYPE_AGG_COL = f'{COLUMN_NAMES.production_type}_agg'


def get_demand_data(folder: str, file_suffix: str, climatic_year: int, period: Tuple[datetime, datetime],
                    is_stress_test: bool = False) -> pd.DataFrame:
    # get demand
    logging.debug('Get demand')
    if is_stress_test:
        demand_folder_full = f'{folder}/{INPUT_CY_STRESS_TEST_SUBFOLDER}'
    else:
        demand_folder_full = folder
    demand_file = f'{demand_folder_full}/{DT_FILE_PREFIX.demand}_{file_suffix}.csv'
    df_demand = pd.read_csv(demand_file, sep=FILES_FORMAT.column_sep, decimal=FILES_FORMAT.decimal_sep)
    # then keep only selected period date range and climatic year
    df_demand = filter_input_data(df=df_demand, date_col=COLUMN_NAMES.date,
                                  climatic_year_col=COLUMN_NAMES.climatic_year, period_start=period[0],
                                  period_end=period[1], climatic_year=climatic_year)
    return df_demand


def get_cf_agg_prod_types_tb_read(selected_agg_prod_types: List[str], agg_prod_types_with_cf_data: List[str],
                                  subdt_selec: List[str] = None) -> List[str]:
    if subdt_selec is not None:
        agg_prod_types_tb_read = get_intersection_of_lists(list1=selected_agg_prod_types, list2=subdt_selec)
    else:
        agg_prod_types_tb_read = selected_agg_prod_types
    # list of prod types with CF data
    return [agg_prod_type for agg_prod_type in agg_prod_types_tb_read if agg_prod_type in agg_prod_types_with_cf_data]


def get_res_capa_factors_data(folder: str, file_suffix: str, climatic_year: int, cf_agg_prod_types_tb_read: List[str],
                              aggreg_pt_cf_def: Dict[str, List[str]], period: Tuple[datetime, datetime],
                              is_stress_test: bool = False) -> Optional[pd.DataFrame]:
    """
    Get RES capa. factors (CF) data
    :param folder: in which RES CF data must be read
    :param file_suffix: of files to be read
    :param climatic_year: considered
    :param cf_agg_prod_types_tb_read: list of aggreg. prod. types with CF data to be read
    :param aggreg_pt_cf_def: def. of aggreg. prod. types - the ones with CF data: {agg. pt: list of associated pts}
    :param period: considered (start, end)
    :param is_stress_test: adapt subfolder in which data is to be read accordingly
    """
    logging.debug('Get RES capacity factors')
    date_col = COLUMN_NAMES.date
    # full path to folder in which RES CF data can be read
    if is_stress_test:
        res_cf_folder_full = f'{folder}/{INPUT_CY_STRESS_TEST_SUBFOLDER}'
    else:
        res_cf_folder_full = folder
    # loop over the agg. production types to be read, the ones with CF data
    df_res_cf_list = []
    for agg_prod_type in cf_agg_prod_types_tb_read:
        logging.debug(N_SPACES_MSG * ' ' + f'- For aggreg. prod. type: {agg_prod_type}')
        current_agg_pt_df_res_cf_list = []
        for prod_type in aggreg_pt_cf_def[agg_prod_type]:
            cf_filename = f'{DT_FILE_PREFIX.res_capa_factors}_{prod_type}_{file_suffix}.csv'
            cf_data_file = uniformize_path_os(path_str=f'{res_cf_folder_full}/{cf_filename}')
            if not os.path.exists(cf_data_file):
                logging.warning(
                    2 * N_SPACES_MSG * ' ' + f'RES capa. factor data file does not exist: '
                                             f'{prod_type} not accounted for here')
            else:
                logging.debug(2 * N_SPACES_MSG * ' ' + f'* Prod. type: {prod_type}')
                current_df_res_cf = pd.read_csv(cf_data_file, sep=FILES_FORMAT.column_sep,
                                                decimal=FILES_FORMAT.decimal_sep)
                current_df_res_cf = \
                    filter_input_data(df=current_df_res_cf, date_col=date_col,
                                      climatic_year_col=COLUMN_NAMES.climatic_year,
                                      period_start=period[0], period_end=period[1],
                                      climatic_year=climatic_year)
                if len(current_df_res_cf) == 0:
                    logging.warning(
                        2 * N_SPACES_MSG * ' ' + f'No RES capa. factor data for prod. type '
                                                 f'{prod_type} and climatic year {climatic_year}')
                else:
                    # add column with production type (for later aggreg.)
                    current_df_res_cf[PROD_TYPE_AGG_COL] = agg_prod_type
                    current_agg_pt_df_res_cf_list.append(current_df_res_cf)
        if len(current_agg_pt_df_res_cf_list) == 0:
            logging.warning(
                N_SPACES_MSG * ' ' + f'No data available for aggregate RES prod. type '
                                     f'{agg_prod_type} -> not accounted for in UC model here')
        else:
            df_res_cf_list.extend(current_agg_pt_df_res_cf_list)
    # concatenate, aggreg. over prod type of same aggreg. type and avg
    if len(df_res_cf_list) == 0:
        return None
    agg_cf_data_read = (
        set_aggreg_cf_prod_types_data(df_cf_list=df_res_cf_list, pt_agg_col=PROD_TYPE_AGG_COL,
                                      date_col=date_col, val_col=COLUMN_NAMES.value))
    return agg_cf_data_read


def get_installed_gen_capas_data(folder: str, file_suffix: str, country: str, aggreg_pt_gen_capa_def,
                                 selected_agg_prod_types: List[str]) -> Optional[pd.DataFrame]:
    # TODO: type
    # get installed generation capacity data
    logging.debug(
        'Get installed generation capacities (1 file per country and year)')
    gen_capa_data_file = f'{folder}/{DT_FILE_PREFIX.generation_capas}_{file_suffix}.csv'
    prod_type_col = COLUMN_NAMES.production_type
    if not os.path.exists(gen_capa_data_file):
        logging.warning(f'Generation capas data file does not exist: {country} not accounted for here')
        return None

    df_gen_capa = pd.read_csv(gen_capa_data_file, sep=FILES_FORMAT.column_sep, decimal=FILES_FORMAT.decimal_sep)
    # Keep sanitize prod. types col values
    df_gen_capa[prod_type_col] = df_gen_capa[prod_type_col].apply(gen_capa_pt_str_sanitizer)
    # Keep only selected aggreg. prod. types
    df_gen_capa = (
        set_aggreg_col_based_on_corresp(df=df_gen_capa, col_name=prod_type_col,
                                        created_agg_col_name=PROD_TYPE_AGG_COL, val_cols=GEN_CAPA_SUBDT_COLS,
                                        agg_corresp=aggreg_pt_gen_capa_def, common_aggreg_ope=AggregOpeNames.sum)
    )
    df_gen_capa = \
        selec_in_df_based_on_list(df=df_gen_capa, selec_col=PROD_TYPE_AGG_COL, selec_vals=selected_agg_prod_types)
    return df_gen_capa


def set_final_hydro_key_cols(hydro_dt: str) -> List[str]:
    key_cols = deepcopy(HYDRO_KEY_COLUMNS[hydro_dt])
    # week and day idx columns have been removed when reading and processing
    for col in [COLUMN_NAMES.day, COLUMN_NAMES.week]:
        if col in key_cols:
            key_cols.remove(col)
    # not to be saved in df of a given country (with all fields of same value)
    zone_col = COLUMN_NAMES.zone
    key_cols.remove(zone_col)
    # if data wo climatic year, but added to have uniform format hereafter
    if COLUMN_NAMES.climatic_year not in key_cols:
        key_cols.append(COLUMN_NAMES.climatic_year)
    return key_cols


def get_hydro_data(hydro_dt: str, folder: str, countries: List[str], climatic_year: int,
                   period: Tuple[datetime, datetime]) -> Optional[Dict[str, pd.DataFrame]]:
    """
    Get hydro. data - with generic function for the different (sub) datatypes: ror prod., inflows, extreme levels
    Args:
        hydro_dt: hydro datatype considered
        folder: in which data is to be read
        countries: to be considered
        climatic_year: idem
        period: idem

    Returns: {country: associated df with date and climatic year - with unique value - as 'key' columns}
    """
    logging.debug(f'Get {hydro_dt} data (1 file over all countries and years)')
    df_hydro_data = read_and_process_hydro_data(hydro_dt=hydro_dt, folder=folder)
    date_col = COLUMN_NAMES.date
    period_start = period[0]
    period_end = period[1]
    df_hydro_data = filter_input_data(df=df_hydro_data, date_col=date_col, climatic_year_col=COLUMN_NAMES.climatic_year,
                                      period_start=period_start, period_end=period_end, climatic_year=climatic_year)
    # resample and distribute to hourly values
    # end date to resample -> to include the 23h of last date in data (under convention that period end is EXCLUDED)
    min_date_data = min(df_hydro_data[date_col])
    # in case of weekly data if period_start is not a Monday it can be strictly before min date in data
    # -> would lead to missing data
    start_date_resample = min(period_start, min_date_data)
    end_date_resample = period_end - timedelta(hours=1)
    value_cols = HYDRO_VALUE_COLUMNS[hydro_dt]
    key_cols = set_final_hydro_key_cols(hydro_dt=hydro_dt)
    per_country_hydro_data = {}
    for country in countries:
        # either day to hours or week to hours
        resample_divisor = 24 if HYDRO_TS_GRANULARITY[hydro_dt] == 'day' else 7 * 24
        fill_na_vals = HYDRO_LEVELS_RESAMPLE_FILLNA_VALS  # only used for extreme-levels of reservoir -> no limit
        current_country_df = (
            selec_in_df_based_on_list(df=df_hydro_data, selec_col=COLUMN_NAMES.zone, selec_vals=[country],
                                      rm_selec_col=True))
        if len(current_country_df) > 0:
            resample_method = HYDRO_DATA_RESAMPLE_METHODS[hydro_dt]
            per_country_hydro_data[country] = (
                resample_and_distribute(df=current_country_df, date_col=date_col, value_cols=value_cols,
                                        key_cols=key_cols, method=resample_method, start_date=start_date_resample,
                                        end_date=end_date_resample, resample_divisor=resample_divisor,
                                        fill_na_vals=fill_na_vals, freq='h')
            )
        else:  # no data for current country
            logging.warning(f'No {hydro_dt} data obtained for country {country}')
            per_country_hydro_data[country] = pd.DataFrame()
    return per_country_hydro_data


def separate_hydro_extr_levels_data(hydro_extr_levels_data: Dict[str, pd.DataFrame],
                                    rename_value_col: bool = True) \
        -> Tuple[Dict[str, pd.DataFrame], Dict[str, pd.DataFrame]]:
    """
    From {country: df containing both min and max levels data} to two separate dictionaries
    Args:
        hydro_extr_levels_data:
        rename_value_col:

    Returns: {country: df with min level data}, {country: df with max level data}
    """
    climatic_year_col = COLUMN_NAMES.climatic_year
    hydro_min_level_data = {}
    hydro_max_level_data = {}
    cols_min_level = [COLUMN_NAMES.date, climatic_year_col, COLUMN_NAMES.min_value]
    cols_max_level = [COLUMN_NAMES.date, climatic_year_col, COLUMN_NAMES.max_value]
    for country, df in hydro_extr_levels_data.items():
        if len(df) == 0:  # no data obtained
            hydro_min_level_data[country] = df
            hydro_max_level_data[country] = df
        else:
            df_min_level = df[cols_min_level]
            df_max_level = df[cols_max_level]
            # TODO: avoid cast to float beforehand of climatic year (because of appli
            #  of ffill method in resample_and_distribute?)
            df_min_level[climatic_year_col] = df_min_level[climatic_year_col].astype(int)
            df_max_level[climatic_year_col] = df_max_level[climatic_year_col].astype(int)
            if rename_value_col:
                df_min_level = df_min_level.rename(columns={COLUMN_NAMES.min_value: COLUMN_NAMES.value})
                df_max_level = df_max_level.rename(columns={COLUMN_NAMES.max_value: COLUMN_NAMES.value})
            hydro_min_level_data[country] = df_min_level
            hydro_max_level_data[country] = df_max_level
    return hydro_min_level_data, hydro_max_level_data


def overwrite_gen_capas_data(df_gen_capa: pd.DataFrame, new_power_capas: Dict[str, Dict[str, float]],
                             country: str) -> pd.DataFrame:
    if df_gen_capa is not None and country in new_power_capas:
        logging.info(f'OVERWRITTEN ERAA prod. capacity values, in MW: {new_power_capas[country]}')
        for agg_prod_type, new_capa_val in new_power_capas[country].items():
            df_gen_capa.loc[
                df_gen_capa[PROD_TYPE_AGG_COL] == agg_prod_type, 'power_capacity'] = new_capa_val
    return df_gen_capa


def add_failure_asset_to_capas_data(df_gen_capa: pd.DataFrame, failure_power_capa: float) -> pd.DataFrame:
    failure_df = pd.DataFrame.from_dict({
        PROD_TYPE_AGG_COL: [ProdTypeNames.failure],
        ERAAParamNames.power_capacity: [int(failure_power_capa)],  # cast to int if float in JSON input file
        ERAAParamNames.power_capacity_turbine: [0.0],
        ERAAParamNames.power_capacity_pumping: [0.0],
        ERAAParamNames.power_capacity_injection: [0.0],
        ERAAParamNames.power_capacity_offtake: [0.0],
        ERAAParamNames.energy_capacity: [0.0]
    })
    return pd.concat([df_gen_capa, failure_df], ignore_index=True)


def capa_info_log(df_gen_capa: pd.DataFrame):
    # get dict. with only power capacity values to get less verbose logs
    power_capa_dict = create_dict_from_cols_in_df(df=df_gen_capa, key_col=PROD_TYPE_AGG_COL, val_col='power_capacity')
    logging.info(f'-> power capacity values, in MW: {power_capa_dict}')


def calc_cf_capa_prod(df_gen_capa: pd.DataFrame, df_agg_cf: pd.DataFrame, cf_agg_prod_types_tb_read: List[str],
                      capas_aggreg_pt_with_cf: Dict[str, int]) -> (Dict[str, pd.DataFrame], List[str], List[str]):
    value_col = COLUMN_NAMES.value
    pts_with_capa_from_arg = []  # prod types with capacity value taken from arg. (not ERAA data)
    pts_wo_cf_data = []  # prod types without CF data obtained...
    cf_capa_prod = {}
    for agg_prod_type in cf_agg_prod_types_tb_read:
        # get current capa either from fixed data provided as arg of this function
        if agg_prod_type in capas_aggreg_pt_with_cf:
            current_capa = capas_aggreg_pt_with_cf[agg_prod_type]
            pts_with_capa_from_arg.append(agg_prod_type)
        else:  # or from (ERAA) dataset data
            current_capa = df_gen_capa.loc[df_gen_capa[PROD_TYPE_AGG_COL] == agg_prod_type, 'power_capacity'].values[0]
        current_cf_data = df_agg_cf[df_agg_cf[PROD_TYPE_AGG_COL] == agg_prod_type]
        if len(current_cf_data) > 0:
            cf_capa_prod[agg_prod_type] = current_capa * np.array(current_cf_data[value_col])
        else:
            pts_wo_cf_data.append(agg_prod_type)
    return cf_capa_prod, pts_with_capa_from_arg, pts_wo_cf_data


def calc_net_demand(df_demand: pd.DataFrame, df_gen_capa: pd.DataFrame, df_agg_cf: pd.DataFrame,
                    cf_agg_prod_types_tb_read: List[str], capas_aggreg_pt_with_cf: Dict[str, int],
                    df_hydro_ror_prod: pd.DataFrame = None) \
        -> (pd.DataFrame, List[str]):
    """
    Calculate net demand
    :param df_demand: df with demand data
    :param df_gen_capa: idem generation capas ones
    :param df_agg_cf: idem, CF ones
    :param cf_agg_prod_types_tb_read: list of pt with CF data to be used for calculation
    :param capas_aggreg_pt_with_cf: {pt name: capa value to be used}; in order to be able to overwrite ERAA capa values
    for some cases (e.g., data analysis)
    :param df_hydro_ror_prod: prod from hydro ROR units
    :returns df with net demand, and list of prod types for which (RES) capacity values have been set from data
    provided in Python arg, and not from ERAA data (in data folder of this project)
    """
    value_col = COLUMN_NAMES.value
    # TODO: directly in pd to avoid creation of np arrays?
    # convert to float so that subtraction of CF can be done hereafter
    current_np_net_demand = np.array(df_demand[value_col]).astype(np.float64)
    cf_capa_prod, pts_with_capa_from_arg, pts_wo_cf_data = (
        calc_cf_capa_prod(df_gen_capa=df_gen_capa, df_agg_cf=df_agg_cf,
                          cf_agg_prod_types_tb_read=cf_agg_prod_types_tb_read,
                          capas_aggreg_pt_with_cf=capas_aggreg_pt_with_cf)
    )
    current_np_net_demand -= sum(cf_capa_prod.values())
    if df_hydro_ror_prod is not None and len(df_hydro_ror_prod) > 0:
        current_np_net_demand -= np.array(df_hydro_ror_prod[value_col])
    df_net_demand = deepcopy(df_demand)
    df_net_demand[value_col] = current_np_net_demand
    # warning if prod. types without CF data obtained -> not taken into account here...
    if len(pts_wo_cf_data) > 0:
        logging.warning(f'No capa. factor data available to account for {pts_wo_cf_data} in net demand calculation')
    return df_net_demand, pts_with_capa_from_arg


def capa_from_arg_for_info_log(data_type: str, prod_types_with_capa_from_arg: List[str],
                               capas_aggreg_pt_with_cf: Dict[str, int]):
    if len(prod_types_with_capa_from_arg) > 0:
        used_capas_from_arg = {pt: capas_aggreg_pt_with_cf[pt] for pt in prod_types_with_capa_from_arg}
        logging.info(f'For {data_type} calculation, the following prod types have capa values used '
                     f'from arg, in MW: {used_capas_from_arg}')


def get_interco_capas_data(folder: str, countries: List[str], year: int) -> Optional[dict]:
    logging.info('Get interconnection capacities (1 file with data of all countries and years)')
    interco_capas_data_file = f'{folder}/{DT_FILE_PREFIX.interco_capas}_{year}.csv'
    if not os.path.exists(interco_capas_data_file):
        msg_prefix = 'Interconnection capas data file does not exist'
        n_countries = len(countries)
        if n_countries > 1:
            raise Exception(f'{msg_prefix}: impossible to run UC model given that '
                            f'{n_countries} > 1 countries considered')
        else:
            logging.warning(msg_prefix)
        return None
    # read
    df_interco_capas = pd.read_csv(interco_capas_data_file, sep=FILES_FORMAT.column_sep,
                                   decimal=FILES_FORMAT.decimal_sep)
    # and select information needed for selected countries
    df_interco_capas = select_interco_capas(df_intercos_capa=df_interco_capas, countries=countries)
    # set as dictionary
    tuple_key_col = 'tuple_key'
    df_interco_capas[tuple_key_col] = \
        df_interco_capas.apply(lambda col: (col[COLUMN_NAMES.zone_origin], col[COLUMN_NAMES.zone_destination]),
                               axis=1)
    return create_dict_from_cols_in_df(df=df_interco_capas, key_col=tuple_key_col, val_col=COLUMN_NAMES.value)


def get_data_for_gen_unit_with_e_capa(capa_data_dict: Dict[str, float]) -> Dict[str, float]:
    """
    Get data for a generation unit with energy capacity attribute -> hydro or stock asset
    :param capa_data_dict: {capa. attr. name IN ERAA DATA: value}
    :returns {capa. attr. name IN PyPSA framework: value}
    """
    current_asset_data = {}
    energy_capacity = capa_data_dict[ERAAParamNames.energy_capacity]
    # first check if hydro-like asset, with power capa turbine/pumping attributes
    power_capacity_turbine = capa_data_dict[ERAAParamNames.power_capacity_turbine]
    power_capacity_pumping = capa_data_dict[ERAAParamNames.power_capacity_pumping]
    if power_capacity_turbine > 0:
        p_nom = max(abs(power_capacity_turbine), abs(power_capacity_pumping))
        p_min_pu = power_capacity_pumping / p_nom
        p_max_pu = power_capacity_turbine / p_nom
        current_asset_data[GEN_UNITS_PYPSA_PARAMS.power_capa] = p_nom
        current_asset_data[GEN_UNITS_PYPSA_PARAMS.min_power_pu] = p_min_pu
        current_asset_data[GEN_UNITS_PYPSA_PARAMS.capa_factors] = p_max_pu
        # max hours for storage-like assets (energy capa/power capa)
        max_hours = energy_capacity / p_nom
        current_asset_data[GEN_UNITS_PYPSA_PARAMS.max_hours] = max_hours
    # then if stock-like asset, with power capa injection/offtake attributes
    power_capacity_injection = capa_data_dict[ERAAParamNames.power_capacity_injection]
    power_capacity_offtake = capa_data_dict[ERAAParamNames.power_capacity_offtake]
    if power_capacity_injection > 0:
        p_nom = max(abs(power_capacity_injection), abs(power_capacity_offtake))
        p_min_pu = -power_capacity_offtake / p_nom
        p_max_pu = power_capacity_injection / p_nom
        current_asset_data[GEN_UNITS_PYPSA_PARAMS.power_capa] = p_nom
        current_asset_data[GEN_UNITS_PYPSA_PARAMS.min_power_pu] = p_min_pu
        current_asset_data[GEN_UNITS_PYPSA_PARAMS.capa_factors] = p_max_pu
        max_hours = energy_capacity / p_nom
        current_asset_data[GEN_UNITS_PYPSA_PARAMS.max_hours] = max_hours
    return current_asset_data


def complete_country_data(per_country_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """
    Replace None values by empty dfs
    """
    empty_df = pd.DataFrame()
    return {country: empty_df if val is None else val for country, val in per_country_data.items()}


def check_if_from_eraa_data(param_key: str, complem_params_pt: Dict[str, str]) -> bool:
    """
    :param param_key: key used for parameter in ele-europe_params_fixed.json
    :param complem_params_pt: dict {param key: where to extract from} for current prod. type
    """
    return param_key in complem_params_pt and complem_params_pt[param_key] == 'from_eraa_data'


@dataclass
class Dataset:
    agg_prod_types_with_cf_data: List[str]
    source: str = 'eraa_2023.2'
    is_stress_test: bool = False
    demand: Dict[str, pd.DataFrame] = None  # {country: df of data}
    net_demand: Dict[str, pd.DataFrame] = None  # idem
    fatal_prod: Dict[str, pd.DataFrame] = None  # idem
    agg_cf_data: Dict[str, pd.DataFrame] = None  # idem
    agg_gen_capa_data: Dict[str, pd.DataFrame] = None  # idem
    interco_capas: Dict[Tuple[str, str], float] = None  # {(origin country, dest. country): interco. capa. value}
    hydro_ror_data: Dict[str, pd.DataFrame] = None  # Run-of-River prod data # TODO: typing
    hydro_inflows_data: Dict[str, pd.DataFrame] = None  # TODO: typing
    hydro_reservoir_levels_min_data: Dict[str, pd.DataFrame] = None  # TODO: typing
    hydro_reservoir_levels_max_data: Dict[str, pd.DataFrame] = None  # TODO: typing
    # {country: list of associated generation units data}
    generation_units_data: Dict[str, List[GenerationUnitData]] = None

    def get_countries_data(self, uc_run_params: UCRunParams, aggreg_prod_types_def: Dict[str, Dict[str, List[str]]],
                           datatypes_selec: List[str] = None, subdt_selec: List[str] = None,
                           capas_aggreg_pt_with_cf: Dict[str, int] = None):
        """
        Get ERAA data necessary for the selected countries
        :param uc_run_params: UC run parameters, from which main reading infos will be obtained
        :param aggreg_prod_types_def: per-datatype definition of aggreg. to indiv. production types
        :param datatypes_selec: list of datatypes for which data must be read
        :param subdt_selec: list of sub-datatypes for which data must be read
        :param capas_aggreg_pt_with_cf: capacities of prod types with CF data to be used for prod. values calculation
        :returns: {country: df with demand of this country}, {country: df with - per aggreg. prod type CF},
        {country: df with installed generation capas}, df with all interconnection capas (for considered 
        countries and year)
        """
        # default is to read all data, excepting net demand (only used for data-analysis)
        if datatypes_selec is None:
            datatypes_selec = list(DATATYPE_NAMES.__dict__.values())
            # remove datatypes that are used only for data-analysis, and not to be used by default
            datatypes_selec.remove(DATATYPE_NAMES.net_demand)
            datatypes_selec.remove(DATATYPE_NAMES.fatal_production)
        # and not to apply capa. values fixed in arg
        if capas_aggreg_pt_with_cf is None:
            capas_aggreg_pt_with_cf = {}

        # get - per datatype - folder names
        demand_folder = os.path.join(INPUT_ERAA_FOLDER, DT_SUBFOLDERS.demand)
        res_cf_folder = os.path.join(INPUT_ERAA_FOLDER, DT_SUBFOLDERS.res_capa_factors)
        gen_capas_folder = os.path.join(INPUT_ERAA_FOLDER, DT_SUBFOLDERS.generation_capas)
        interco_capas_folder = os.path.join(INPUT_ERAA_FOLDER, DT_SUBFOLDERS.interco_capas)
        hydro_folder = os.path.join(INPUT_ERAA_FOLDER, DT_SUBFOLDERS.hydro)

        self.demand = {}
        self.fatal_prod = {}
        self.net_demand = {}
        self.agg_cf_data = {}
        self.agg_gen_capa_data = {}
        self.hydro_ror_data = {}
        self.hydro_inflows_data = {}
        self.hydro_reservoir_levels_min_data = {}
        self.hydro_reservoir_levels_max_data = {}

        dts_tb_read = deepcopy(datatypes_selec)
        # datatypes to be added to list of read ones, to be able to obtain net demand
        if DATATYPE_NAMES.net_demand in datatypes_selec:
            dts_tb_read.extend([DATATYPE_NAMES.demand, DATATYPE_NAMES.installed_capa, DATATYPE_NAMES.capa_factor,
                                DATATYPE_NAMES.hydro_ror])
            dts_tb_read = list(set(dts_tb_read))

        # idem for fatal prod.
        if DATATYPE_NAMES.fatal_production in datatypes_selec:
            dts_tb_read.extend([DATATYPE_NAMES.installed_capa, DATATYPE_NAMES.capa_factor, DATATYPE_NAMES.hydro_ror])
            dts_tb_read = list(set(dts_tb_read))

        # hydro. data is concatenated over all countries in hydro data -> read it once
        # TODO: merge/loop (how to for assignment depending on hydro datatype?)
        if DATATYPE_NAMES.hydro_ror in dts_tb_read:
            if subdt_selec is None or DATATYPE_NAMES.hydro_ror in subdt_selec:
                self.hydro_ror_data \
                    = get_hydro_data(hydro_dt=DATATYPE_NAMES.hydro_ror, folder=hydro_folder,
                                     countries=uc_run_params.selected_countries,
                                     climatic_year=uc_run_params.selected_climatic_year,
                                     period=(uc_run_params.uc_period_start, uc_run_params.uc_period_end)
                                     )
        if DATATYPE_NAMES.hydro_inflows in dts_tb_read:
            self.hydro_inflows_data = (
                get_hydro_data(hydro_dt=DATATYPE_NAMES.hydro_inflows, folder=hydro_folder,
                               countries=uc_run_params.selected_countries,
                               climatic_year=uc_run_params.selected_climatic_year,
                               period=(uc_run_params.uc_period_start, uc_run_params.uc_period_end))
            )
        # both extr levels data in same file -> get data once
        if DATATYPE_NAMES.hydro_levels_min in dts_tb_read or DATATYPE_NAMES.hydro_levels_max in dts_tb_read:
            hydro_extr_levels_data = (
                get_hydro_data(hydro_dt=DATATYPE_NAMES.hydro_levels_min, folder=hydro_folder,
                               countries=uc_run_params.selected_countries,
                               climatic_year=uc_run_params.selected_climatic_year,
                               period=(uc_run_params.uc_period_start, uc_run_params.uc_period_end))
            )
            # from {country: df containing both min and max levels data} to two separate dictionaries
            self.hydro_reservoir_levels_min_data, self.hydro_reservoir_levels_max_data = (
                separate_hydro_extr_levels_data(hydro_extr_levels_data=hydro_extr_levels_data)
            )
        # loop over countries for per country data files
        for country in uc_run_params.selected_countries:
            logging.info(3 * '#' + f' For country: {country}')
            logging.info(f'With selected aggreg. prod. types: {uc_run_params.selected_prod_types[country]}')
            # read csv files for different types of data
            current_suffix = f'{uc_run_params.selected_target_year}_{country}'  # common suffix to all ERAA data files
            if DATATYPE_NAMES.demand in dts_tb_read:
                # get demand
                current_df_demand = get_demand_data(folder=demand_folder, file_suffix=current_suffix,
                                                    climatic_year=uc_run_params.selected_climatic_year,
                                                    period=(uc_run_params.uc_period_start, uc_run_params.uc_period_end),
                                                    is_stress_test=self.is_stress_test)
                # if demand selected add it to dataset
                if DATATYPE_NAMES.demand in datatypes_selec:
                    self.demand[country] = current_df_demand

            if DATATYPE_NAMES.capa_factor in dts_tb_read:
                # get RES capacity factor data
                logging.debug('Get RES capacity factors')
                if DATATYPE_NAMES.capa_factor in datatypes_selec:
                    self.agg_cf_data[country] = None
                # get list of agg. prod. types for which data must be read
                cf_agg_prod_types_tb_read = (
                    get_cf_agg_prod_types_tb_read(selected_agg_prod_types=uc_run_params.selected_prod_types[country],
                                                  agg_prod_types_with_cf_data=self.agg_prod_types_with_cf_data,
                                                  subdt_selec=subdt_selec)
                )
                # get RES CF data for these prod. types
                agg_cf_data_read = (
                    get_res_capa_factors_data(folder=res_cf_folder, file_suffix=current_suffix,
                                              climatic_year=uc_run_params.selected_climatic_year,
                                              cf_agg_prod_types_tb_read=cf_agg_prod_types_tb_read,
                                              aggreg_pt_cf_def=aggreg_prod_types_def[DATATYPE_NAMES.capa_factor],
                                              period=(uc_run_params.uc_period_start, uc_run_params.uc_period_end),
                                              is_stress_test=self.is_stress_test)
                )

                if len(cf_agg_prod_types_tb_read) > 0 and agg_cf_data_read is None:
                    logging.warning(
                        N_SPACES_MSG * ' ' + f'No RES data available for country {country} '
                                             f'-> not accounted for in UC model here')
                elif DATATYPE_NAMES.capa_factor in datatypes_selec:
                    self.agg_cf_data[country] = agg_cf_data_read

            if DATATYPE_NAMES.installed_capa in dts_tb_read:
                # fixed capas for agg. prod types with CF data not accounted for here
                if capas_aggreg_pt_with_cf is not None and len(capas_aggreg_pt_with_cf) > 0:
                    logging.warning(f'ERAA capas data for following agg. prod types (with CF data) will not be '
                                    f'accounted for: {capas_aggreg_pt_with_cf} -> replaced by values provided in arg, '
                                    f'for net demand calculation only')
                # get ERAA capas for gen. assets
                current_df_gen_capa = (
                    get_installed_gen_capas_data(folder=gen_capas_folder, file_suffix=current_suffix,
                                                 country=country,
                                                 aggreg_pt_gen_capa_def=
                                                 aggreg_prod_types_def[DATATYPE_NAMES.installed_capa],
                                                 selected_agg_prod_types=uc_run_params.selected_prod_types[country])
                )
                # add failure fictive one
                if ProdTypeNames.failure in uc_run_params.selected_prod_types[country]:
                    current_df_gen_capa = (
                        add_failure_asset_to_capas_data(df_gen_capa=current_df_gen_capa,
                                                        failure_power_capa=uc_run_params.failure_power_capa)
                    )
                # overwrite capacity values - based on the ones provided in input JSON file(s)
                current_df_gen_capa = (
                    overwrite_gen_capas_data(df_gen_capa=current_df_gen_capa,
                                             new_power_capas=uc_run_params.capacities_tb_overwritten, country=country)
                )
                if DATATYPE_NAMES.installed_capa in datatypes_selec:
                    self.agg_gen_capa_data[country] = current_df_gen_capa
                capa_info_log(df_gen_capa=current_df_gen_capa)

            if DATATYPE_NAMES.fatal_production in datatypes_selec:
                # TODO: include hydro ror here ?
                cf_capa_prod, pts_with_capa_from_arg, pts_wo_cf_data = (
                    calc_cf_capa_prod(df_gen_capa=current_df_gen_capa, df_agg_cf=agg_cf_data_read,
                                      cf_agg_prod_types_tb_read=cf_agg_prod_types_tb_read,
                                      capas_aggreg_pt_with_cf=capas_aggreg_pt_with_cf))
                # from dict {pt name: np prod profile} to df "production_type_agg", "date", "value" to unify format
                # get dates from CF data - on which data selection has been applied
                first_agg_pt = list(cf_capa_prod)[0]
                # selecting only the dates for a given agg. pt (other each date will be repeated...
                # nber of agg. pt times)
                current_dates = (
                    list(agg_cf_data_read.loc[agg_cf_data_read['production_type_agg'] == first_agg_pt, COLUMN_NAMES.date]))
                n_dates = len(current_dates)
                dfs_lst = []
                for agg_pt, prod_prof in cf_capa_prod.items():
                    dfs_lst.append(pd.DataFrame({'production_type_agg': n_dates * [agg_pt],
                                                 COLUMN_NAMES.date: current_dates, COLUMN_NAMES.value: prod_prof}))
                # with other data
                self.fatal_prod[country] = pd.concat(dfs_lst)
                capa_from_arg_for_info_log(data_type=DATATYPE_NAMES.fatal_production,
                                           prod_types_with_capa_from_arg=pts_with_capa_from_arg,
                                           capas_aggreg_pt_with_cf=capas_aggreg_pt_with_cf)

            if DATATYPE_NAMES.net_demand in datatypes_selec:
                # ror production of current country
                if country in self.hydro_ror_data:
                    current_ror_prod = self.hydro_ror_data[country]
                else:
                    current_ror_prod = None
                current_df_net_demand, pts_with_capa_from_arg = (
                    calc_net_demand(df_demand=current_df_demand, df_gen_capa=current_df_gen_capa,
                                    df_agg_cf=agg_cf_data_read, cf_agg_prod_types_tb_read=cf_agg_prod_types_tb_read,
                                    capas_aggreg_pt_with_cf=capas_aggreg_pt_with_cf, df_hydro_ror_prod=current_ror_prod)
                )
                self.net_demand[country] = current_df_net_demand
                capa_from_arg_for_info_log(data_type=DATATYPE_NAMES.net_demand,
                                           prod_types_with_capa_from_arg=pts_with_capa_from_arg,
                                           capas_aggreg_pt_with_cf=capas_aggreg_pt_with_cf)

        if DATATYPE_NAMES.interco_capa in datatypes_selec:
            interco_capas = (
                get_interco_capas_data(folder=interco_capas_folder, countries=uc_run_params.selected_countries,
                                       year=uc_run_params.selected_target_year)
            )
            # add interco capas values set by user
            if interco_capas is not None:
                interco_capas |= uc_run_params.interco_capas_tb_overwritten
            self.interco_capas = interco_capas

    def complete_data(self):
        """
        Replace None values by empty dfs in all dict {country: df of data}
        """
        # TODO: see cases leading to None data at this stage... and if to be treated before - and merge following cases
        self.demand = complete_country_data(per_country_data=self.demand)
        self.fatal_prod = complete_country_data(per_country_data=self.fatal_prod)
        self.net_demand = complete_country_data(per_country_data=self.net_demand)
        self.agg_cf_data = complete_country_data(per_country_data=self.agg_cf_data)
        self.agg_gen_capa_data = complete_country_data(per_country_data=self.agg_gen_capa_data)
        self.hydro_ror_data = complete_country_data(per_country_data=self.hydro_ror_data)
        self.hydro_inflows_data = complete_country_data(per_country_data=self.hydro_inflows_data)
        self.hydro_reservoir_levels_min_data = complete_country_data(
            per_country_data=self.hydro_reservoir_levels_min_data)
        self.hydro_reservoir_levels_max_data = complete_country_data(
            per_country_data=self.hydro_reservoir_levels_max_data)

    def get_agg_prod_types(self, country: str) -> List[str]:
        return list(set(self.agg_gen_capa_data[country][PROD_TYPE_AGG_COL]))

    def get_generation_units_data(self, uc_run_params: UCRunParams, pypsa_unit_params_per_agg_pt: Dict[str, dict],
                                  units_complem_params_per_agg_pt: Dict[str, Dict[str, str]]):
        """
        Get generation units data to create them hereafter
        :param uc_run_params
        :param pypsa_unit_params_per_agg_pt: dict of per aggreg. prod type main Pypsa params
        :param units_complem_params_per_agg_pt: # for each aggreg. prod type, a dict. {complem. param name: source
        - "from_json_tb_modif"/"from_eraa_data"}
        """
        # TODO: make subcases per type of generator below to have a more explicit code
        # TODO: marginal costs/efficiency, from FuelSources??
        countries = list(self.agg_gen_capa_data)
        # TODO: set as global constants/unify...
        power_capa_key = 'power_capa'
        capa_factor_key = 'capa_factors'
        inflow_key = 'inflow'  # TODO: as a constant
        soc_level_extr_key = 'soc_level_extr'
        self.generation_units_data = {}
        for country in countries:
            logging.debug(f'- for country {country}')
            self.generation_units_data[country] = []
            # get list of assets to be treated from capa. data
            agg_prod_types = self.get_agg_prod_types(country=country)
            # initialize set of params for each unit by using pypsa default values
            # TODO: introduce function with explicit name for this init stage
            current_assets_data = {agg_pt: pypsa_unit_params_per_agg_pt[agg_pt] for agg_pt in agg_prod_types}
            # and loop over pt to add complementary params
            for agg_pt in agg_prod_types:
                logging.debug(N_SPACES_MSG * ' ' + f'* for aggreg. prod. type {agg_pt}')
                # set and add asset name
                current_assets_data[agg_pt][GEN_UNITS_PYPSA_PARAMS.name] = (
                    set_gen_unit_name(country=country, agg_prod_type=agg_pt)
                )
                # and 'type' (the aggreg. prod types used here, with a direct corresp. to PyPSA generators; 
                # made explicit in JSON fixed params files)
                current_assets_data[agg_pt]['type'] = agg_pt
                # extract data of current agg. pt (and country) as dict {capa attr. name: value}
                current_pt_capa_data_dict = (
                    create_dict_from_df_row(df=self.agg_gen_capa_data[country],
                                            col_and_val_for_selec=(PROD_TYPE_AGG_COL, agg_pt))
                )
                # power capacity, for all assets
                # TODO: see why int cast not ok before that... because of failure with possibly float power capa
                #  data in JSON input params file?
                power_capacity = int(current_pt_capa_data_dict[ERAAParamNames.power_capacity])
                power_capacity_turbine = current_pt_capa_data_dict[ERAAParamNames.power_capacity_turbine]
                energy_capacity = current_pt_capa_data_dict[ERAAParamNames.energy_capacity]
                is_storage_like = energy_capacity > 0
                if agg_pt in units_complem_params_per_agg_pt and len(units_complem_params_per_agg_pt[agg_pt]) > 0:
                    # add pnom attribute if needed
                    if check_if_from_eraa_data(param_key=power_capa_key,
                                               complem_params_pt=units_complem_params_per_agg_pt[agg_pt]):
                        logging.debug(2 * N_SPACES_MSG * ' ' + f'-> add {power_capa_key}')
                        current_assets_data[agg_pt][GEN_UNITS_PYPSA_PARAMS.power_capa] = int(power_capacity)

                    # add pmax_pu when variable for RES/fatal units
                    if check_if_from_eraa_data(param_key=capa_factor_key,
                                               complem_params_pt=units_complem_params_per_agg_pt[agg_pt]):
                        logging.debug(2 * N_SPACES_MSG * ' ' + f'-> add {capa_factor_key}')
                        current_pt_res_cf_data = (
                            self.agg_cf_data)[country][self.agg_cf_data[country][PROD_TYPE_AGG_COL] == agg_pt]
                        current_assets_data[agg_pt][GEN_UNITS_PYPSA_PARAMS.capa_factors] = (
                            np.array(current_pt_res_cf_data[COLUMN_NAMES.value])
                        )
                    # add inflow when it applies
                    if check_if_from_eraa_data(param_key=inflow_key,
                                               complem_params_pt=units_complem_params_per_agg_pt[agg_pt]):
                        logging.debug(2 * N_SPACES_MSG * ' ' + f'-> add {inflow_key}')
                        current_pt_inflow_data = self.hydro_inflows_data[country]
                        # set column according to type of hydro asset
                        inflow_value_col = 'cum_inflow_into_reservoirs' if agg_pt == ProdTypeNames.hydro_reservoir \
                            else 'cum_nat_inflow_into_pump-storage_reservoirs'
                        try:
                            current_inflows_data = np.array(current_pt_inflow_data[inflow_value_col])
                        except:
                            logging.warning(f'Issue to access inflows data for {country} and {agg_pt} -> set to 0')
                            current_inflows_data = 0  # Q: ok to set constant float and not vector for this PyPSA attr.?
                        current_assets_data[agg_pt][GEN_UNITS_PYPSA_PARAMS.inflow] = current_inflows_data
                    # add soc extreme levels when it applies
                    if check_if_from_eraa_data(param_key=soc_level_extr_key,
                                               complem_params_pt=units_complem_params_per_agg_pt[agg_pt]):
                        logging.debug(2 * N_SPACES_MSG * ' ' + f'-> add {soc_level_extr_key} (min and max)')
                        current_pt_soc_level_min_data = self.hydro_reservoir_levels_min_data[country]
                        try:
                            current_soc_level_min_data = np.array(current_pt_soc_level_min_data[COLUMN_NAMES.value])
                        except:
                            logging.warning(
                                f'Issue to access SOC level min data for {country} and {agg_pt} -> set to 0')
                            current_soc_level_min_data = 0  # Q: ok to set constant float and not vector for this PyPSA attr.?
                        current_pt_soc_level_max_data = self.hydro_reservoir_levels_max_data[country]
                        try:
                            current_soc_level_max_data = np.array(current_pt_soc_level_max_data[COLUMN_NAMES.value])
                        except:
                            logging.warning(
                                f'Issue to access SOC level min data for {country} and {agg_pt} -> set to 0')
                            current_soc_level_max_data = 1e12  # Q: ok to set constant float and not a vector for this PyPSA attr.?
                        current_assets_data[agg_pt][GenUnitsCustomParams.soc_min] = current_soc_level_min_data
                        current_assets_data[agg_pt][GenUnitsCustomParams.soc_max] = current_soc_level_max_data

                # specific parameters for failure
                elif agg_pt == ProdTypeNames.failure:
                    current_assets_data[agg_pt][GEN_UNITS_PYPSA_PARAMS.power_capa] = power_capacity
                    current_assets_data[agg_pt][GEN_UNITS_PYPSA_PARAMS.marginal_cost] = uc_run_params.failure_penalty
                    current_assets_data[agg_pt][GEN_UNITS_PYPSA_PARAMS.committable] = False
                # storage-like assets
                if is_storage_like:
                    current_agg_pt_data = get_data_for_gen_unit_with_e_capa(capa_data_dict=current_pt_capa_data_dict)
                    current_assets_data[agg_pt] |= current_agg_pt_data
                    # overwrite specific turbine/pumping (injection/offtake) max values by power capa. if provided
                    if power_capacity > 0:
                        current_assets_data[agg_pt][GEN_UNITS_PYPSA_PARAMS.power_capa] = power_capacity
                # DSR with reinjection??
                elif power_capacity_turbine > 0:
                    p_nom = abs(power_capacity_turbine)
                    current_assets_data[agg_pt][GEN_UNITS_PYPSA_PARAMS.power_capa] = p_nom
                    current_assets_data[agg_pt][GEN_UNITS_PYPSA_PARAMS.min_power_pu] = 0
                    current_assets_data[agg_pt][GEN_UNITS_PYPSA_PARAMS.capa_factors] = 1
                    # idem overwrite by power capa. value if provided
                    if power_capacity > 0:
                        current_assets_data[agg_pt][GEN_UNITS_PYPSA_PARAMS.power_capa] = power_capacity

                self.generation_units_data[country].append(GenerationUnitData(**current_assets_data[agg_pt]))

    def set_generation_units_data(self, gen_units_data: Dict[str, List[GenerationUnitData]]):
        self.generation_units_data = gen_units_data

    def dump_gen_units_data_to_json(self, filepath: str):
        logging.info(f'Save PyPSA generation units data into JSON file: {filepath}')
        data_dict = {country: [unit_data.serialize() for unit_data in gen_units_data]
                     for country, gen_units_data in self.generation_units_data.items()}
        json_dump(data=data_dict, filepath=filepath)

    def set_committable_param_to_false(self):
        per_country_modif_values = {}
        for country, units_data in self.generation_units_data.items():
            for unit_data in units_data:
                if unit_data.committable:
                    if country not in per_country_modif_values:
                        per_country_modif_values[country] = []
                    per_country_modif_values[country].append(unit_data.name)
                unit_data.committable = False
        logging.info(f'Set committable PyPSA parameter to False, i.e. run without dynamic constraints; '
                     f'modified values (True -> False) for units: {per_country_modif_values}')

    def control_min_pypsa_params_per_gen_units(self, pypsa_min_unit_params_per_agg_pt: Dict[str, List[str]]):
        """
        Control that minimal PyPSA parameter infos has been provided before creating generation units
        """
        pypsa_params_errors_list = []
        # loop over countries
        for country, gen_units_data in self.generation_units_data.items():
            # and unit in them
            for elt_unit_data in gen_units_data:
                current_unit_type = elt_unit_data.type
                pypsa_min_unit_params_set = set(pypsa_min_unit_params_per_agg_pt[current_unit_type])
                params_with_init_val_set = set(elt_unit_data.get_non_none_attr_names())
                missing_pypsa_params = list(pypsa_min_unit_params_set - params_with_init_val_set)
                if len(missing_pypsa_params) > 0:
                    current_unit_name = elt_unit_data.name
                    current_msg = (f'country {country}, unit name {current_unit_name} and type {current_unit_type} '
                                   f'-> {missing_pypsa_params}')
                    pypsa_params_errors_list.append(current_msg)
        if len(pypsa_params_errors_list) > 0:
            print_errors_list(error_name='on "minimal" PyPSA gen. units parameters; missing ones for',
                              errors_list=pypsa_params_errors_list)
        else:
            logging.info('PyPSA NEEDED PARAMETERS FOR GENERATION UNITS CREATION HAVE BEEN LOADED!')

    def get_hydro_params_for_extr_levels_const(self) -> (
    Dict[str, np.ndarray], Dict[str, np.ndarray], Dict[str, float]):
        hydro_reservoirs_data = {country: select_gen_units_data(gen_units_data=units_data,
                                                                countries=[set_country_trigram(country=country)],
                                                                unit_types=[ProdTypeNames.hydro_reservoir])
                                 for country, units_data in self.generation_units_data.items()}
        hydro_soc_min = {elt.name: elt.soc_min
                         for c, reservoirs_data in hydro_reservoirs_data.items() for elt in reservoirs_data}
        hydro_soc_max = {elt.name: elt.soc_max
                         for c, reservoirs_data in hydro_reservoirs_data.items() for elt in reservoirs_data}
        # energy capacity, obtained as power capacity * max_hours duration
        hydro_e_capa = {elt.name: float(elt.max_hours * elt.p_nom)
                        for c, reservoirs_data in hydro_reservoirs_data.items() for elt in reservoirs_data}
        return hydro_soc_min, hydro_soc_max, hydro_e_capa
