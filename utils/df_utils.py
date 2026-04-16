import logging
import warnings

import numpy as np
import pandas as pd
from typing import Dict, List
from datetime import datetime

from common.long_term_uc_io import ResampleMethods
from utils.basic_utils import get_key_of_val


def cast_df_col_as_date(df: pd.DataFrame, date_col: str, date_format: str) -> pd.DataFrame:
    df[date_col] = df[date_col].apply(lambda x: datetime.strptime(x, date_format))
    return df


def selec_in_df_based_on_list(df: pd.DataFrame, selec_col, selec_vals: list, rm_selec_col=False) -> pd.DataFrame:
    val = df.loc[df[selec_col].isin(selec_vals)]
    if rm_selec_col:
        val = val.drop(columns=[selec_col])
    return val


def get_tuples_from_columns(df: pd.DataFrame, columns: list) -> List[tuple]:
    """
    Extract a list of tuples from specified columns in a DataFrame
    """
    # Validate columns
    missing_cols = [col for col in columns if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Columns not found in DataFrame: {missing_cols}")

    # Convert subset to list of tuples
    return [tuple(row) for row in df[columns].to_numpy()]


def concatenate_dfs(dfs: List[pd.DataFrame], reset_index: bool = True) -> pd.DataFrame:
    df_concat = pd.concat(dfs, axis=0)
    if reset_index:
        df_concat = df_concat.reset_index(drop=True)
    return df_concat


def set_aggreg_col_based_on_corresp(df: pd.DataFrame, col_name: str, created_agg_col_name: str, val_cols: List[str],
                                    agg_corresp: Dict[str, List[str]], common_aggreg_ope: str,
                                    other_col_for_agg: str = None) -> pd.DataFrame:
    """
    Set aggreg. column based on a correspondence {aggreg. value: list of corresp. (indiv.) values}
    :param df
    :param col_name: of the (indiv.) keys
    :param created_agg_col_name: of the aggreg. keys
    :param val_cols: list of value columns
    :param agg_corresp
    :param common_aggreg_ope: name of aggreg. operation to be applied on value columns in considered df
    :param other_col_for_agg
    :returns: df after having applied aggreg. operation
    """
    df[created_agg_col_name] = df[col_name].apply(get_key_of_val, args=(agg_corresp,))
    agg_operations = {col: common_aggreg_ope for col in val_cols}
    if other_col_for_agg is not None:
        gpby_cols = [created_agg_col_name, other_col_for_agg]
    else:
        gpby_cols = created_agg_col_name
    df = df.groupby(gpby_cols).agg(agg_operations).reset_index()
    return df


def get_subdf_from_date_range(df: pd.DataFrame, date_col: str, date_min: datetime, date_max: datetime) -> pd.DataFrame:
    """
    Get values in a dataframe from a date range
    """
    df_range = df[(date_min <= df[date_col]) & (df[date_col] < date_max)]
    return df_range


def create_dict_from_cols_in_df(df: pd.DataFrame, key_col, val_col) -> dict:
    df_to_dict = df[[key_col, val_col]]
    return dict(pd.MultiIndex.from_frame(df_to_dict))


def create_dict_from_df_row(df: pd.DataFrame, col_and_val_for_selec: tuple = None, key_cols: list = None,
                            rm_col_for_selec: bool = True) -> dict:
    col_for_selec = None
    if col_and_val_for_selec is not None:
        col_for_selec = col_and_val_for_selec[0]
        val_for_selec = col_and_val_for_selec[1]
        df = df.loc[df[col_for_selec] == val_for_selec]

    # columns used as key -> all as default
    if key_cols is None:
        key_cols = list(df.columns)

    dict_from_df = {col: df[col].iloc[0] for col in key_cols}

    # remove column used for row selection?
    if col_and_val_for_selec is not None and rm_col_for_selec:
        del dict_from_df[col_for_selec]

    return dict_from_df


def rename_df_columns(df: pd.DataFrame, old_to_new_cols: dict) -> pd.DataFrame:
    # catch SettingWithCopyWarning
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        df.rename(columns=old_to_new_cols, inplace=True)
    return df


def replace_none_values_in_df(df: pd.DataFrame, per_col_repl_values: dict, key_cols: list = None, 
                              deactivate_verbose_warn: bool = True) -> pd.DataFrame:
    if key_cols is None:
        key_cols = list(set(df.columns) - set(per_col_repl_values))
    cols_with_none_vals = {}
    for col, default_val in per_col_repl_values.items():
        df_with_na = df[df[col].isna()]
        if len(df_with_na) > 0:
            keys_with_none_vals = get_tuples_from_columns(df=df_with_na, columns=key_cols)
            cols_with_none_vals[col] = keys_with_none_vals
            df = df.fillna({col: default_val})
    if len(cols_with_none_vals) > 0:
        repl_values_applied = {col: default_val for col, default_val in per_col_repl_values.items()
                               if col in cols_with_none_vals}
        if not deactivate_verbose_warn:
            logging.warning(f'There were none values in df associated to keys: {cols_with_none_vals}'
                            f'\n-> replaced by {repl_values_applied}')
    return df


def replace_all_none_values_in_df(df: pd.DataFrame, value_tb_set) -> pd.DataFrame:
    df.fillna(value=value_tb_set, inplace=True)
    return df


def set_key_columns(col_names: list, tuple_values: List[tuple], n_repeat: int = None) -> pd.DataFrame:
    """
    :param col_names: list of key column names
    :param tuple_values
    :param n_repeat: number of repetition of each tuple in the df e.g., when dates are commonly used per
    each tuple value
    """
    if n_repeat is None:
        n_repeat = 1
    n_keys = len(tuple_values[0])
    concat_keys = np.concatenate([np.array(elt).reshape(1, n_keys) for elt in tuple_values], axis=0)
    concat_keys = np.repeat(concat_keys, n_repeat, axis=0)
    return pd.DataFrame(data=concat_keys, columns=col_names)


def resample_and_distribute(df: pd.DataFrame, date_col: str, value_cols: list, method: str, start_date: datetime = None, 
                            end_date: datetime = None, resample_divisor: float = None, fill_na_vals: dict = None, 
                            key_cols: list = None, freq: str = 'h') -> pd.DataFrame:
    """
    Resample a DataFrame from daily to a finer frequency (e.g., hourly),
    distribute numeric values proportionally, and repeat key columns.
    Params:
    start_date: of the resampling, to possibly include some time-slots before first value in df
    end_date: idem, after the last date value in df
    Returns:
    -------
    pd.DataFrame
        Resampled DataFrame with proportional distribution and reset index.
    """
    df.set_index(date_col, inplace=True)

    # Determine the end date for resampling
    first_date = df.index.min()
    if start_date is not None:
        if start_date > first_date:
            raise ValueError('Start date cannot be later than the first index date for df resampling')
        first_date = start_date
        
    last_date = df.index.max()
    if end_date is not None:
        if end_date < last_date:
            raise ValueError('End date cannot be earlier than the last index date for df reasmpling')
        last_date = end_date

    if method == ResampleMethods.uniform_distrib:
        # Resample to target frequency
        resampled = df.resample(freq).ffill()
        # Reindex to the end (resp. by the start) and ffil (resp. bfill)
        full_range_end = pd.date_range(df.index.min(), last_date, freq=freq)
        resampled = resampled.reindex(full_range_end, method='ffill')
        full_range = pd.date_range(first_date, last_date, freq=freq)
        resampled = resampled.reindex(full_range, method='bfill')
        # Resample division?
        if resample_divisor is not None:
            for col in value_cols:
                resampled[col] = resampled[col] / resample_divisor
        
    elif method == ResampleMethods.all_at_first_ts:
        full_range = pd.date_range(first_date, last_date, freq=freq)
        resampled = df.reindex(full_range)
        resampled = resampled.fillna(fill_na_vals)

    # Forward+backward-fill key columns if provided
    if key_cols:
        for col in key_cols:
            resampled[col] = resampled[col].ffill().bfill()

    # Reset index so date becomes a column
    return resampled.reset_index().rename(columns={'index': date_col})


def sort_out_cols_with_zero_values(df: pd.DataFrame, abs_val_threshold: float) -> pd.DataFrame:
    df = df.loc[:, (df.abs() >= abs_val_threshold).any(axis=0)]
    return df


if __name__ == '__main__':
    data = {
        'date': pd.date_range('2025-11-10', periods=3, freq='D'),
        'region': ['Europe', 'Europe', 'Europe'],
        'value': [240, 480, 720],
        'value2': [24, 48, 72]
    }
    df = pd.DataFrame(data)

    # Apply function
    hourly_df = resample_and_distribute(df, date_col='date', value_cols=['value', 'value2'], key_cols=['region'],
                                        freq='h', resample_divisor=24, start_date=datetime(2025, 11, 9), end_date=datetime(2025,11,12,23),
                                        method=ResampleMethods.all_at_first_ts, fill_na_vals={'value': 0, 'value2': 1000})
    bob = 1
