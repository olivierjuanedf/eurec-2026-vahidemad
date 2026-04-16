import logging
import os
from typing import List, Optional
import pandas as pd
from datetime import datetime

from common.constants.aggreg_operations import AggregOpeNames
from common.constants.datatypes import DATATYPE_NAMES
from common.long_term_uc_io import COLUMN_NAMES, DATE_FORMAT, FILES_FORMAT, HYDRO_VALUE_COLUMNS, HYDRO_FILES, \
    HYDRO_KEY_COLUMNS, HYDRO_DEFAULT_VALUES
from utils.basic_utils import str_sanitizer, robust_cast_str_to_float
from utils.dates import set_date_from_year_and_iso_idx, set_date_from_year_and_day_idx
from utils.df_utils import cast_df_col_as_date, concatenate_dfs, selec_in_df_based_on_list, \
    get_subdf_from_date_range, replace_none_values_in_df


def filter_input_data(df: pd.DataFrame, date_col: str, climatic_year_col: str, period_start: datetime, 
                      period_end: datetime, climatic_year: int) -> pd.DataFrame:
    # If ERAA date format not automatically cast by pd
    first_date = df[date_col].iloc[0]
    if not isinstance(first_date, datetime):
        df = cast_df_col_as_date(df=df, date_col=date_col, date_format=DATE_FORMAT)
    # keep only wanted date range
    df_filtered = get_subdf_from_date_range(df=df, date_col=date_col, date_min=period_start, date_max=period_end).copy()
    # then selected climatic year
    if climatic_year_col in df_filtered.columns:
        df_filtered = selec_in_df_based_on_list(df=df_filtered, selec_col=climatic_year_col, selec_vals=[climatic_year])
    # cases with data inependent of climatic years (e.g. hydro reservoir min/max levels)
    # -> add climatic year col (+ selected value in it) to have uniform formats hereafter
    else:
        df_filtered.loc[:, climatic_year_col] = climatic_year
    return df_filtered


def set_aggreg_cf_prod_types_data(df_cf_list: List[pd.DataFrame], pt_agg_col: str, date_col: str,
                                  val_col: str) -> pd.DataFrame:
    # concatenate, aggreg. over prod type of same aggreg. type and avg
    df_cf_agg = concatenate_dfs(dfs=df_cf_list)
    df_cf_agg = df_cf_agg.groupby([pt_agg_col, date_col]).agg({val_col: AggregOpeNames.mean}).reset_index()
    return df_cf_agg


def gen_capa_pt_str_sanitizer(gen_capa_prod_type: str) -> str:
    # very ad-hoc operation
    sanitized_gen_capa_pt = gen_capa_prod_type.replace(' - ', ' ')
    sanitized_gen_capa_pt = str_sanitizer(raw_str=sanitized_gen_capa_pt, 
                                          ad_hoc_replacements={'gas_': 'gas', '(': '', ')': ''})
    return sanitized_gen_capa_pt


def select_interco_capas(df_intercos_capa: pd.DataFrame, countries: List[str]) -> pd.DataFrame:
    selection_col = 'selected'
    # add selection column
    origin_col = COLUMN_NAMES.zone_origin
    destination_col = COLUMN_NAMES.zone_destination
    df_intercos_capa[selection_col] = \
        df_intercos_capa.apply(lambda col: 1 if (col[origin_col] in countries 
                                                 and col[destination_col] in countries) else 0, axis=1)
    # keep only lines with both origin and destination zones in the list of available countries
    df_intercos_capa = df_intercos_capa[df_intercos_capa[selection_col] == 1]
    # remove selection column
    all_cols = list(df_intercos_capa.columns)
    all_cols.remove(selection_col)
    df_intercos_capa = df_intercos_capa[all_cols]
    return df_intercos_capa


def read_and_process_hydro_data(hydro_dt: str, folder: str, rm_week_and_day_cols: bool = True) \
        -> Optional[pd.DataFrame]:
    """
    Read and process hydro data files -> that share some common structure (in particular with only week - and day - idx
    values, i.o. dates)
    Returns: df with read data
    """
    hydro_file = f'{folder}/{HYDRO_FILES[hydro_dt]}'
    if not os.path.exists(hydro_file):
        logging.warning(f'{hydro_dt.capitalize()} data file does not exist: not accounted for here')
        return None

    df_hydro = pd.read_csv(hydro_file, sep=FILES_FORMAT.column_sep, decimal=FILES_FORMAT.decimal_sep)
    # robust cast to numeric values -> got some pbs with data... TODO: fix this more properly
    value_cols = HYDRO_VALUE_COLUMNS[hydro_dt]
    for col in value_cols:
        df_hydro[col] = df_hydro[col].apply(robust_cast_str_to_float)
    # replace none values by default ones
    df_hydro = replace_none_values_in_df(df=df_hydro, per_col_repl_values=HYDRO_DEFAULT_VALUES[hydro_dt],
                                         key_cols=HYDRO_KEY_COLUMNS[hydro_dt])
    # specific treatment for hydro weekly/daily data -> set date column based on week(/and day) values
    df_cols = list(df_hydro.columns)
    week_col = COLUMN_NAMES.week
    day_col = COLUMN_NAMES.day
    date_col = COLUMN_NAMES.date
    if day_col not in df_cols:  # set date from week index only
        # add day column with 1 for all (i.e. Monday)
        df_hydro[day_col] = 1
        df_cols.append(day_col)
        # remove rows with invalid week idx (> 52)
        init_len = len(df_hydro)
        df_hydro = df_hydro[df_hydro[week_col] < 53]
        new_len = len(df_hydro)
        if new_len < init_len:
            logging.warning(f'{init_len - new_len} rows suppressed in {hydro_dt} data due to invalid week idx (> 52)')
        # set date column based on week and day=1 index values
        df_hydro[date_col] = (
            df_hydro.apply(lambda row:
                           set_date_from_year_and_iso_idx(year=1900, week_idx=row[week_col], day_idx=row[day_col]),
                           axis=1)
        )
    else:  # only from day index from 1 to 365
        df_hydro[date_col] = (df_hydro[day_col]
                                       .apply(lambda x: set_date_from_year_and_day_idx(year=1900, day_idx=x))
                                       )
    if rm_week_and_day_cols:
        cols_tb_rmed = [week_col]
        if day_col in df_cols:
            cols_tb_rmed.append(day_col)
        df_hydro.drop(columns=cols_tb_rmed, inplace=True)
    return df_hydro
