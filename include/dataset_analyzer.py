import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import product
from typing import List, Union, Dict, Tuple, Optional

import numpy as np
import pandas as pd

from common.constants.data_analysis_types import ANALYSIS_TYPES, ANALYSIS_TYPES_PLOT, AVAILABLE_ANALYSIS_TYPES
from common.constants.datatypes import DatatypesNames, UNITS_PER_DT, DATATYPE_NAMES
from common.constants.extract_eraa_data import ERAADatasetDescr, FICTIVE_CALENDAR_YEAR
from common.constants.temporal import DATE_FORMAT_IN_JSON, MAX_DATE_IN_DATA, N_DAYS_DATA_ANALYSIS_DEFAULT
from common.error_msgs import uncoherent_param_stop
from common.long_term_uc_io import OUTPUT_DATA_ANALYSIS_FOLDER
from common.plot_params import PlotParams
from include.uc_timeseries import set_uc_ts_name, UCTimeseries
from utils.basic_utils import random_draw_in_list, check_all_values_equal
from utils.dates import robust_date_parser, set_year_in_date, set_temporal_period_str
from utils.df_utils import selec_in_df_based_on_list
from utils.plot import FigureStyle
from utils.type_checker import CheckerNames, apply_params_type_check

AVAILABLE_DATA_TYPES = list(DatatypesNames.__annotations__.values())
AGG_PROD_TYPE_KEY = 'aggreg_prod_types'  # TODO[Q2OJ]: cleaner way to set/get it?
RAW_TYPES_FOR_CHECK = {'analysis_type': CheckerNames.is_str, 'data_type': CheckerNames.is_str,
                       AGG_PROD_TYPE_KEY: CheckerNames.is_str_or_list_of_str,
                       'country': CheckerNames.is_str_or_list_of_str,
                       'year': CheckerNames.is_int_or_list_of_int, 'climatic_year': CheckerNames.is_int_or_list_of_int}
DEFAULT_CY = 'first'


def set_period_for_analysis(period_start: str, period_end: str) -> (datetime, datetime):
    # first try to cast provided dates to datetime
    if period_start is not None:
        period_start = robust_date_parser(my_date=period_start, raise_warning=True)
    if period_end is not None:
        period_end = robust_date_parser(my_date=period_end, raise_warning=True)
    # then set default values
    if period_start is None:
        period_start = datetime(year=1900, month=1, day=1)
    if period_end is None:
        if period_start is not None:
            logging.info(f'Period end set from start {period_start: %Y/%m/%d} and '
                         f'default number of days in period {N_DAYS_DATA_ANALYSIS_DEFAULT}')
            period_end = (
                min(MAX_DATE_IN_DATA, period_start + timedelta(days=N_DAYS_DATA_ANALYSIS_DEFAULT)))
        else:
            period_end = datetime(year=1900, month=12, day=31)
    return period_start, period_end


def set_period_to_common_year(period_start: datetime, period_end: datetime) -> (datetime, datetime):
    period_end_year = period_end.year
    period_start_year = period_start.year
    if not period_end_year == period_start_year:
        period_end_bis = datetime(year=period_start_year, month=period_end.month, day=period_end.day)
        if period_end_bis < period_start:
            period_start = (
                datetime(year=period_end_year, month=period_start.month, day=period_start.day)
            )
            common_year = period_end_year
            changed_extr = 'start'
        else:
            period_end = period_end_bis
            common_year = period_start_year
            changed_extr = 'end'
        logging.warning(f'Start and end of period do not share same year ({period_start_year} '
                        f'and {period_end_year} resp.) -> common year {common_year} will be considered, '
                        f'by changing {changed_extr} of period date')
    return period_start, period_end


def set_period_to_fixed_year(period_start: datetime, period_end: datetime, year: int) -> (datetime, datetime):
    # TODO: more robust code for this function (if not same calendar in period start/end years and in year...) ->
    #  reset start/end in year so that period has same nber of days
    period_start_year = period_start.year
    period_end_year = period_end.year
    if period_start_year == period_end_year and period_start_year == year:
        return period_start, period_end

    logging.info(f'{period_start:%Y/%m/%d} and {period_end:%Y/%m/%d} not in fixed year {year} -> modified')
    period_start = set_year_in_date(my_date=period_start, new_year=year)
    period_end = set_year_in_date(my_date=period_end, new_year=year)
    return period_start, period_end


def get_default_climatic_year(available_climatic_years: List[int]) -> int:
    if DEFAULT_CY == 'first':
        default_cy = min(available_climatic_years)
    elif DEFAULT_CY == 'last':
        default_cy = max(available_climatic_years)
    else:  # random draw
        default_cy = random_draw_in_list(my_list=available_climatic_years)
    return default_cy


def stop_if_coherence_check_error(obj_checked, errors_list: List[str]):
    # stop if any error
    if len(errors_list) > 0:
        uncoherent_param_stop(param_errors=errors_list)
    else:
        logging.info('Input data analysis PARAMETERS ARE COHERENT!')
        logging.info(f'ANALYSIS CAN START with parameters: {str(obj_checked)}')


@dataclass
class ExtraParamNames:
    capas_aggreg_pt_with_cf: str = 'capas_aggreg_pt_with_cf'


@dataclass
class DataAnalExtraParams:
    values: dict
    index: int = 1
    label: str = None

    def __repr__(self) -> str:
        repr_str = f'{self.label}: ' if self.label is not None else ''
        repr_str += str(self.values)
        return repr_str

    def process(self):
        if self.label is None:
            self.label = f'case {self.index}'

    def coherence_check(self, eraa_data_descr: ERAADatasetDescr):
        errors_list = []
        # check that names of extra-params values are coherent
        all_extra_param_names = set(ExtraParamNames.capas_aggreg_pt_with_cf)
        current_param_names = set(self.values)
        unknown_param_names = list(current_param_names - all_extra_param_names)
        if len(unknown_param_names) > 0:
            errors_list.append(f'Unknown extra-param names (keys of value dict.): {unknown_param_names}')

        # check that aggreg. prod. types are in allowed list
        fixed_cf_capas_key = ExtraParamNames.capas_aggreg_pt_with_cf
        if fixed_cf_capas_key in self.values:
            cf_capas_keys = list(self.values[fixed_cf_capas_key])
            unknown_cf_capas = [elt for elt in cf_capas_keys if elt not in eraa_data_descr.available_aggreg_prod_types]
            if len(unknown_cf_capas) > 0:
                errors_list.append(f'Unknown aggreg. prod. type with capa. factor data: {unknown_cf_capas}')

        # stop if any error
        stop_if_coherence_check_error(obj_checked=self, errors_list=errors_list)


@dataclass
class DataAnalysis:
    analysis_type: str
    data_type: str
    countries: Union[str, List[str]]  # in JSON can be str or list of str; when reading convert all to List[str]
    years: Union[int, List[int]]  # idem above with int or List[int]
    climatic_years: Union[int, List[int]]
    aggreg_prod_types: Union[str, List[str]] = None  # idem above with str or List[str]
    period_start: Union[str, datetime] = None  # in JSON str, then datetime after parsing data
    period_end: Union[str, datetime] = None  # idem
    # Extra parameters to be used for data analysis, e.g. RES installed capacities - that can be used for
    # net demand calculation
    # in JSON dict or list of dicts, then list objects after parsing data
    extra_params: Union[dict, List[dict], List[DataAnalExtraParams]] = None

    def __repr__(self) -> str:
        sep_in_str = '\n- '
        repr_str = 'ERAA data analysis with params:'
        repr_str += f'{sep_in_str}of type {self.analysis_type}'
        repr_str += f'{sep_in_str}for data type: {self.data_type}'
        repr_str += f'{sep_in_str}countries: {self.countries}'
        repr_str += f'{sep_in_str}years: {self.years}'
        repr_str += f'{sep_in_str}climatic years: {self.climatic_years}'
        if not self.aggreg_prod_types == [None]:
            repr_str += f'{sep_in_str}aggreg. prod. types: {self.aggreg_prod_types}'

        if self.period_start is not None and self.period_end is not None:
            temp_period_str = (
                set_temporal_period_str(min_date=self.period_start, max_date=self.period_end,
                                        print_year=False, in_letter=True)
            )
            repr_str += f'{sep_in_str}period: {temp_period_str}'
        if not self.extra_params == [None]:
            repr_str += f'{sep_in_str}extra-params: {str(self.extra_params)}'

        return repr_str

    def check_types(self):
        """
        Check coherence of types
        """
        dict_for_check = self.__dict__
        if self.aggreg_prod_types is None:
            del dict_for_check[AGG_PROD_TYPE_KEY]
        apply_params_type_check(dict_for_check, types_for_check=RAW_TYPES_FOR_CHECK,
                                param_name='Data analysis params - to set the calc./plot to be done')

    def process(self, eraa_data_descr: ERAADatasetDescr):
        # country, year, climatic year, aggreg. prod. types attrs all to List[.]
        if isinstance(self.countries, str):
            self.countries = [self.countries]
        if isinstance(self.years, int):
            self.years = [self.years]
        # set default climatic year for data analysis
        if self.climatic_years is None:
            default_cy = get_default_climatic_year(available_climatic_years=eraa_data_descr.available_climatic_years)
            logging.info(f'Default climatic year {default_cy} used (as not defined in DataAnalysis JSON file)')
            self.climatic_years = [default_cy]
        elif isinstance(self.climatic_years, int):
            self.climatic_years = [self.climatic_years]
        if self.aggreg_prod_types is not None and isinstance(self.aggreg_prod_types, str):
            self.aggreg_prod_types = [self.aggreg_prod_types]
        elif self.aggreg_prod_types is None:
            # in the case of RES capa factors include all prod. types (if no selection in input JSON file)
            if self.data_type == DatatypesNames.capa_factor:
                # get per country and year agg. prod types with CF data (available in ERAA)
                per_country_and_yr_agg_pt_with_cf = \
                    {country:
                         {year:
                              set([prod_type for prod_type in eraa_data_descr.available_aggreg_prod_types[country][year]
                                   if prod_type in eraa_data_descr.agg_prod_types_with_cf_data])
                          for year in self.years
                          }
                     for country in self.countries
                     }
                # check that all sets coincide
                unique_agg_pt_set = check_all_values_equal(d=per_country_and_yr_agg_pt_with_cf)
                if not unique_agg_pt_set:
                    raise Exception(f'Not possible to analyse capa factors data without aggreg. prod. type(s) '
                                    f'selection for multiple countrie(s)*year(s) with different sets of available agg. '
                                    f'prod types with CF data (as product of cases considered): see available '
                                    f'ERAA data {per_country_and_yr_agg_pt_with_cf}')
                first_country = self.countries[0]
                first_year = self.years[0]
                self.aggreg_prod_types = per_country_and_yr_agg_pt_with_cf[first_country][first_year]
            else:
                self.aggreg_prod_types = [None]

        self.period_start, self.period_end = (
            set_period_for_analysis(period_start=self.period_start, period_end=self.period_end)
        )

        if self.extra_params is not None:
            if isinstance(self.extra_params, dict):
                self.extra_params = [self.extra_params]
            extra_params_obj = []
            for i, elt in enumerate(self.extra_params):
                if elt is not None:
                    index = i + 1
                    elt['index'] = index
                    params = DataAnalExtraParams(**elt)
                    params.process()
                    extra_params_obj.append(params)
                else:
                    extra_params_obj.append(None)
            self.extra_params = extra_params_obj
        else:
            self.extra_params = [None]

    def coherence_check(self, eraa_data_descr: ERAADatasetDescr, n_curves_max: int):
        errors_list = []
        # check that analysis type (plot, extract, etc.) is in the list of allowed values
        if self.analysis_type not in AVAILABLE_ANALYSIS_TYPES:
            errors_list.append(f'Unknown data analysis type: {self.analysis_type}')
        # some ad-hoc checks for datatype
        # for production
        if self.data_type == DatatypesNames.fatal_production:
            # check that some aggreg. pt are provided
            if self.aggreg_prod_types == [None]:
                errors_list.append(f'For {self.analysis_type} with {DatatypesNames.fatal_production} some aggreg. '
                                   f'prod. types must be specified')
            else:  # and that they correspond to pt with CF data
                agg_pt_wo_cf_data = set(self.aggreg_prod_types) - set(eraa_data_descr.agg_prod_types_with_cf_data)
                if len(agg_pt_wo_cf_data) > 0:
                    errors_list.append(f'For {self.analysis_type} with {DatatypesNames.fatal_production}, aggreg. prod. '
                                       f'types without CF data: {agg_pt_wo_cf_data}')

        # check country
        unknown_countries = [elt for elt in self.countries if elt not in eraa_data_descr.available_countries]
        if len(unknown_countries) > 0:
            errors_list.append(f'Unknown selected countries: {unknown_countries}')

        # check TY and CY
        unknown_years = [elt for elt in self.years if elt not in eraa_data_descr.available_target_years]
        if len(unknown_years) > 0:
            errors_list.append(f'Unknown target years: {unknown_years}')
        unknown_clim_years = \
            [elt for elt in self.climatic_years if elt not in eraa_data_descr.available_climatic_years
             and elt not in eraa_data_descr.available_climatic_years_stress_test]
        if len(unknown_clim_years) > 0:
            errors_list.append(f'Unknown climatic years: {unknown_clim_years}')

        # check maximal nber of curves
        if self.analysis_type in ANALYSIS_TYPES_PLOT:
            n_curves = len(self.countries) * len(self.years) * len(self.climatic_years)
            attr_sep = ', '
            elts_error_msg = [attr_sep.join(self.countries), attr_sep.join([str(year) for year in self.years]),
                              attr_sep.join([str(cy) for cy in self.climatic_years])]
            for optional_elt in [self.extra_params, self.aggreg_prod_types]:
                if not optional_elt == [None]:
                    n_curves *= len(optional_elt)
                    elts_error_msg.append(attr_sep.join([elt if isinstance(elt, str) else str(elt)
                                                         for elt in optional_elt]))
            if n_curves > n_curves_max:
                msg_suffix = '\n* '.join(elts_error_msg)
                errors_list.append(f'Too many curves for {self.analysis_type}: {n_curves} '
                                   f'(vs. max allowed {n_curves_max}) - with product of cases:\n* {msg_suffix}')

        # coherence of start and end period
        if self.period_end <= self.period_start:
            errors_list.append(f'Period end {self.period_end.strftime(DATE_FORMAT_IN_JSON)} '
                               f'before start {self.period_start.strftime(DATE_FORMAT_IN_JSON)}')

        # restrict to same calendar year to simplify following treatments -> 1900 as the unique one in "modeled" data
        self.period_start, self.period_end = (
            set_period_to_common_year(period_start=self.period_start, period_end=self.period_end)
        )
        self.period_start, self.period_end = (
            set_period_to_fixed_year(period_start=self.period_start, period_end=self.period_end,
                                     year=FICTIVE_CALENDAR_YEAR)
        )

        # stop if any error
        stop_if_coherence_check_error(obj_checked=self, errors_list=errors_list)

    def set_agg_prod_types_to_default_val(self):
        self.aggreg_prod_types = [None]

    def get_dt_suffix_for_output(self) -> Optional[str]:
        # ATTENTION TRICKY ASPECT: agg. prod. types only used for net demand calculation,
        # not to have 1 curve/block of data per case -> set this attr. to [None] after data selection
        if self.data_type == DATATYPE_NAMES.net_demand and not self.aggreg_prod_types == [None]:
            logging.debug('Aggreg. prod. types attr. set to None after data selection for net demand analysis')
            # save first a "datatype-suffix" to identify this case in filename saved
            n_agg_pt = len(self.aggreg_prod_types)
            if n_agg_pt == 1:
                dt_suffix_for_output = f'incl_{self.aggreg_prod_types[0]}'
            else:
                dt_suffix_for_output = f'incl_{n_agg_pt}-aggpts'
            self.set_agg_prod_types_to_default_val()
            return dt_suffix_for_output
        if self.data_type in [DATATYPE_NAMES.capa_factor, DATATYPE_NAMES.fatal_production]:
            n_agg_pt = len(self.aggreg_prod_types)
            # if unique aggreg. pt otherwise neithed legend label nor filename would allow to identify pt
            if n_agg_pt == 1:
                return self.aggreg_prod_types[0]
        return None

    def get_extra_args_idx_to_label_corresp(self) -> Dict[int, str]:
        return {elt.index: elt.label for elt in self.extra_params if elt is not None}

    def apply_analysis(self, per_case_data: Dict[Tuple[str, int, int], pd.DataFrame], fig_style: FigureStyle = None,
                       per_dim_plot_params: Dict[str, PlotParams] = None, extra_params_labels: Dict[int, str] = None,
                       dt_suffix_for_output: str = None):
        """
        Apply 'analysis', either saving data to csv, or plotting it
        :param per_case_data: per tuple (country, year, climatic year) data in a dict. {tuple: df},
        or unique dataframe if unique case considered
        :param fig_style: FigureStyle params, in case a plot be applied
        :param per_dim_plot_params: {plot dimension eg 'zone': parameters to be used for plot color/linestyle/marker}
        :param extra_params_labels: {idx: label} corresp. for extra-parameters (no corresp. for None extra-params)
        :param dt_suffix_for_output: suffix to be added to datatype in output files to identify them in specific cases
        (currently only for net demand case with aggreg. prod. type selection for data selection + calc. but not leading
        to different curves/blocks of data in saved .png/.csv)
        """
        date_col = 'date'
        value_col = 'value'
        uc_ts_name = set_uc_ts_name(data_type=self.data_type, countries=self.countries, years=self.years,
                                    climatic_years=self.climatic_years, extra_params=self.extra_params,
                                    aggreg_prod_types=self.aggreg_prod_types)
        # loop over (country, year, clim_year) of this analysis
        dates = {}
        values = {}
        # get agg. prod. types obtained in data if RES capa factors analysed and no selection requested
        # in input JSON file
        for country, year, clim_year, current_extra_params, agg_pt in (
                product(self.countries, self.years, self.climatic_years, self.extra_params, self.aggreg_prod_types)):
            try:
                extra_params_idx = current_extra_params.index if current_extra_params is not None else None
                # N.B. dates are the same for all agg. prod types - but copied for simplicity here
                # if no agg. pt selection
                if agg_pt is None:
                    current_subdt_data = per_case_data[(country, year, clim_year, extra_params_idx)]
                else:  # multiple sub-dts data concatenated in same df -> select only data for current sub-dt
                    current_subdt_data = (
                        selec_in_df_based_on_list(df=per_case_data[(country, year, clim_year, extra_params_idx)],
                                                  selec_col='production_type_agg', selec_vals=[agg_pt],
                                                  rm_selec_col=True)
                    )
                current_dates = list(current_subdt_data[date_col])
            except:
                logging.error(f'No dates obtained from data {self.data_type}, for (country, year, clim. year, '
                              f'extra-params idx) = ({country}, {year}, {clim_year}, {extra_params_idx}) '
                              f'-> not integrated in this data analysis')
                continue
            # if data available continue analysis (and plot)
            dates[(country, year, clim_year, extra_params_idx, agg_pt)] = \
                [elt_date.replace(year=year) for elt_date in current_dates]
            values[(country, year, clim_year, extra_params_idx, agg_pt)] = np.array(current_subdt_data[value_col])

        uc_timeseries = UCTimeseries(name=uc_ts_name, data_type=self.data_type, dates=dates,
                                     values=values, unit=UNITS_PER_DT[self.data_type])
        # And apply calc./plot... and other operations
        if len(values) == 0:
            logging.warning(f'No data obtained for type {self.data_type} -> analysis (plot/save to .csv) not done')
        elif self.analysis_type == ANALYSIS_TYPES.plot:
            uc_timeseries.plot(output_dir=OUTPUT_DATA_ANALYSIS_FOLDER, fig_style=fig_style,
                               per_dim_plot_params=per_dim_plot_params, extra_params_labels=extra_params_labels,
                               dt_suffix_for_output=dt_suffix_for_output)
        elif self.analysis_type == ANALYSIS_TYPES.plot_duration_curve:
            uc_timeseries.plot_duration_curve(output_dir=OUTPUT_DATA_ANALYSIS_FOLDER, fig_style=fig_style,
                                              per_dim_plot_params=per_dim_plot_params,
                                              extra_params_labels=extra_params_labels,
                                              dt_suffix_for_output=dt_suffix_for_output)
        elif self.analysis_type in [ANALYSIS_TYPES.extract, ANALYSIS_TYPES.extract_to_mat]:
            # TODO[debug]: to_matrix_format not an arg of this method..., complem_columns missing...
            to_matrix = True if self.analysis_type == ANALYSIS_TYPES.extract_to_mat else False
            uc_timeseries.to_csv(output_dir=OUTPUT_DATA_ANALYSIS_FOLDER, extra_params_labels=extra_params_labels,
                                 dt_suffix_for_output=dt_suffix_for_output)
