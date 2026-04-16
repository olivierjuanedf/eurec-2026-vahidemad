from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
import logging

from common.constants.extract_eraa_data import ERAADatasetDescr
from common.constants.optimisation import ZoneAndTempProdSumConstraint, CustomConstraintNames, ConstMultCoeffNames, \
    CustomConstraintDirection
from common.constants.prod_types import ProdTypeNames
from common.constants.temporal import DATE_FORMAT_IN_JSON, MIN_DATE_IN_DATA, \
    MAX_DATE_IN_DATA, N_DAYS_UC_DEFAULT
from common.constants.uc_json_inputs import ALL_KEYWORD
from common.error_msgs import uncoherent_param_stop
from include.timeseries import Timeseries
from utils.basic_utils import are_lists_eq
from utils.dates import get_period_str
from utils.eraa_utils import set_interco_to_tuples


def check_unique_int_value(param_name: str, param_value) -> Optional[str]:
    if not isinstance(param_value, int):
        f'Unique {param_name} to be provided; must be an int'
    else:
        return None


UNKNOWN_CY_ERROR = 'Unknown climatic year'
UNKNOWN_TY_ERROR = 'Unknown target year'


def coherent_target_year(errors_list: List[str]) -> bool:
    return all([UNKNOWN_TY_ERROR not in elt for elt in errors_list])


def count_custom_const_per_type(constraints_lst: List[ZoneAndTempProdSumConstraint]) -> Dict[str, int]:
    n_const_per_type = {}
    for constraint in constraints_lst:
        current_type = constraint.type
        if current_type not in n_const_per_type:
            n_const_per_type[current_type] = 1
        else:
            n_const_per_type[current_type] += 1
    return n_const_per_type


@dataclass
class UCRunParams:
    selected_climatic_year: int
    selected_countries: List[str]
    selected_target_year: int
    selected_prod_types: Dict[str, Optional[List[str]]]
    uc_period_start: Union[str, datetime]
    uc_period_end: Union[str, datetime] = None
    failure_power_capa: float = None
    failure_penalty: float = None
    interco_capas_tb_overwritten: Union[Dict[str, float], Dict[Tuple[str, str], float]] = field(default_factory=dict)
    capacities_tb_overwritten: Dict[str, Optional[Dict[str, float]]] = field(default_factory=dict)
    updated_fuel_sources_params: Dict[str, Dict[str, Optional[float]]] = None
    # to indicate that some parameters have been changed compared to the set of the ones used for CP decision-making
    is_stress_test: bool = None
    # some extra-parameters
    co2_emis_price: float = None  # common over Eur. CO2 emissions price -> used in UC objective function
    max_co2_emis_constraints: dict = None  # data to define max co2 emission constraints
    # sum of production constraint objects, obtained based on previous dicts:
    # sum_{z, t} prod(z, t) * coeff(z, t) <= ub (or >=)
    sum_prod_constraints: List[ZoneAndTempProdSumConstraint] = None

    def __repr__(self):
        repr_sep = '\n- '
        repr_str = 'UC long-term model run with params:'
        n_countries = len(self.selected_countries)
        repr_str += f'{repr_sep}{n_countries} country(ies): {self.selected_countries}'
        period_str = get_period_str(period_start=self.uc_period_start, period_end=self.uc_period_end)
        repr_str += f'{repr_sep}year: {self.selected_target_year}, on period {period_str} (last time-slot excluded)'
        repr_str += f'{repr_sep}climatic year: {self.selected_climatic_year}'
        if len(self.sum_prod_constraints) > 0:
            n_constraints_per_type = count_custom_const_per_type(constraints_lst=self.sum_prod_constraints)
            constraints_msg_elts = [f'{const_nber} {const_type}'
                                    for const_type, const_nber in n_constraints_per_type.items()]
            constraints_msg = '; '.join(constraints_msg_elts)
            repr_str += f'{repr_sep}custom constraints: {constraints_msg}'
        return repr_str

    def process(self, available_countries: List[str], fullfill_selected_pt: bool = True):
        # if dates in str format, cast them as datetime
        # - setting end of period to default value if not provided
        if isinstance(self.uc_period_start, str):
            self.uc_period_start = datetime.strptime(self.uc_period_start, DATE_FORMAT_IN_JSON)
        if self.uc_period_end is None:
            self.uc_period_end = min(MAX_DATE_IN_DATA, self.uc_period_start + timedelta(days=N_DAYS_UC_DEFAULT))
            logging.info(
                f'End of period set to default value: {self.uc_period_end:%Y/%m/%d} (period of {N_DAYS_UC_DEFAULT} '
                f'days (a week with 2 days of "ring guard"); with bound on 1900, Dec. 31th)')
        elif isinstance(self.uc_period_end, str):
            self.uc_period_end = datetime.strptime(self.uc_period_end, DATE_FORMAT_IN_JSON)
        # replace None and missing countries in dict of aggreg. prod. types
        if fullfill_selected_pt:
            for country in available_countries:
                if country not in self.selected_prod_types \
                        or self.selected_prod_types[country] is None:
                    self.selected_prod_types[country] = []

        # empty dict if interco. added values is empty
        if self.interco_capas_tb_overwritten is None:
            self.interco_capas_tb_overwritten = {}
        else:  # set interco. from {zone_origin}2{zone_destination} names to tuples
            interco_tuples = set_interco_to_tuples(interco_names=self.interco_capas_tb_overwritten,
                                                   return_corresp=True)
            self.interco_capas_tb_overwritten = {interco_tuples[key]: val
                                                 for key, val in self.interco_capas_tb_overwritten.items()}
        # keep only updated source params values that are non None
        if self.updated_fuel_sources_params is not None:
            new_updated_fuel_source_params = {}
            for source, params in self.updated_fuel_sources_params.items():
                new_params = {name: val for name, val in params.items() if val is not None}
                if len(new_params) > 0:
                    new_updated_fuel_source_params[source] = new_params
            self.updated_fuel_sources_params = new_updated_fuel_source_params

        # process custom sum-prod. constraints data, e.g. max CO2 emissions one
        self.sum_prod_constraints = []
        # add max CO2 emis constraints
        if self.max_co2_emis_constraints is not None:
            for const_params in self.max_co2_emis_constraints['cases']:
                # create timeseries from upper bound value and timescale
                temporal_granularity = self.max_co2_emis_constraints['temporal_granularity']
                upper_bound_ts = Timeseries(timescale=temporal_granularity, value=const_params['upper_bound'])
                upper_bound_ts.check(period_start=self.uc_period_start, period_end=self.uc_period_end,
                                     with_whole_period_gran=True)
                # set dates associated to upper bound values
                upper_bound_ts.set_dates(period_start=self.uc_period_start, period_end=self.uc_period_end)
                upper_bound_ts.weigh_values(period_start=self.uc_period_start, period_end=self.uc_period_end)
                # multiply extreme values of the series to weigh them according to duration of first/last period (if
                # not full, e.g. week with only 3 days)
                self.sum_prod_constraints.append(
                    ZoneAndTempProdSumConstraint(type=CustomConstraintNames.max_co2_emissions,
                                                 direction=CustomConstraintDirection.lower,
                                                 mult_coeff_name=ConstMultCoeffNames.co2_emis_factor,
                                                 temporal_granularity=temporal_granularity,
                                                 countries=const_params['countries'],
                                                 bound=upper_bound_ts.value)
                )
            # and process + check that they are coherently defined
            for constraint in self.sum_prod_constraints:
                constraint.process()
                constraint.check(available_countries=available_countries)

    def set_is_stress_test(self, avail_cy_stress_test: List[int]):
        self.is_stress_test = self.selected_climatic_year in avail_cy_stress_test

    def coherence_check_ty_and_cy(self, eraa_data_descr: ERAADatasetDescr, stop_if_error: bool = False) -> List[str]:
        errors_list = []
        # check that unique value provided
        year_int_checker = {'target year': self.selected_target_year, 'climatic year': self.selected_climatic_year}
        for year_type, year_val in year_int_checker.items():
            year_error_msg = check_unique_int_value(param_name=year_type, param_value=year_val)
            if year_error_msg is not None:
                errors_list.append(year_error_msg)
        available_climatic_years = eraa_data_descr.available_climatic_years_stress_test if self.is_stress_test \
            else eraa_data_descr.available_climatic_years
        cy_error_suffix = ' (in stress test mode)' if self.is_stress_test else ''
        year_avail_val_checker = {self.selected_target_year:
                                      (eraa_data_descr.available_target_years, UNKNOWN_TY_ERROR, ''),
                                  self.selected_climatic_year:
                                      (available_climatic_years, UNKNOWN_CY_ERROR, cy_error_suffix)}
        for year_val, (available_values, error_prefix, error_suffix) in year_avail_val_checker.items():
            if isinstance(year_val, int) and year_val not in available_values:
                errors_list.append(f'{error_prefix} {year_val}{error_suffix}')
        # stop if any error
        if stop_if_error and len(errors_list) > 0:
            uncoherent_param_stop(param_errors=errors_list)

        return errors_list

    def coherence_check(self, eraa_data_descr: ERAADatasetDescr, add_failure_asset_if_missing: bool = True):
        # start by checking Target Year (TY) and Climatic Year (CY)
        errors_list = self.coherence_check_ty_and_cy(eraa_data_descr=eraa_data_descr)

        # check that there is no repetition of countries
        countries_set = set(self.selected_countries)
        if len(countries_set) < len(self.selected_countries):
            errors_list.append('Repetition in selected countries')

        # check coherence of values with fixed params
        # for selected countries
        unknown_countries = list(countries_set - set(eraa_data_descr.available_countries))
        if len(unknown_countries) > 0:
            errors_list.append(f'Unknown selected country(ies): {unknown_countries}')

        # operation that can be done only if coherent year; otherwise ref. (available) data cannot be obtained
        is_coherent_ty = coherent_target_year(errors_list=errors_list)
        if is_coherent_ty:
            for elt_country, current_agg_pt in self.selected_prod_types.items():
                if current_agg_pt == [ALL_KEYWORD]:
                    self.selected_prod_types[elt_country] = (
                        eraa_data_descr.available_aggreg_prod_types)[elt_country][self.selected_target_year]

        # check that countries in aggreg. prod. types are not repeated, and known
        agg_pt_countries = list(self.selected_prod_types)
        agg_pt_countries_set = set(agg_pt_countries)
        msg_suffix = 'in keys of dict. of aggreg. prod. types selection'
        if len(agg_pt_countries_set) < len(agg_pt_countries):
            errors_list.append(f'Repetition of countries {msg_suffix}')
        unknown_agg_pt_countries = list(agg_pt_countries_set - set(eraa_data_descr.available_countries))
        if len(unknown_agg_pt_countries) > 0:
            errors_list.append(f'Unknown countrie(s) {msg_suffix}: {unknown_agg_pt_countries}')

        # check coherence of prod types in all different params
        agg_pt_countries_with_val = [elt_country for elt_country in agg_pt_countries
                                     if len(self.selected_prod_types[elt_country]) > 0]
        countries_lists = [self.selected_countries, agg_pt_countries_with_val]
        if not are_lists_eq(list_of_lists=countries_lists):
            errors_list.append(
                f'Countries are different in selection list ({self.selected_countries}) versus keys of aggreg. prod. '
                f'types selection dict. - wo None value ({agg_pt_countries_with_val})')

        # add failure asset if not considered for some countries
        if add_failure_asset_if_missing:
            countries_with_added_failure = []
            for country in self.selected_prod_types:
                if ProdTypeNames.failure not in self.selected_prod_types[country]:
                    countries_with_added_failure.append(country)
                    self.selected_prod_types[country].append(ProdTypeNames.failure)
            if len(countries_with_added_failure) > 0:
                logging.info(f'A failure asset has been added to the following countries: '
                             f'{countries_with_added_failure} (to get a feasible UC resolution)')

        # check that aggreg. prod types are not repeated, and known -> can be done only if coherent TY
        if is_coherent_ty:
            msg_suffix = 'in values of dict. of aggreg. prod. types selection, for country'
            for elt_country, current_agg_pt in self.selected_prod_types.items():
                # check can be done only if country keys are known
                if elt_country in unknown_agg_pt_countries:
                    continue
                current_avail_aggreg_pts = (
                    eraa_data_descr.available_aggreg_prod_types)[elt_country][self.selected_target_year]
                current_avail_aggreg_pt_set = set(current_avail_aggreg_pts)
                current_agg_pt_set = set(current_agg_pt)
                if len(current_agg_pt_set) < len(current_agg_pt):
                    errors_list.append(f'Repetition of aggreg. prod. types {msg_suffix} {elt_country}')
                unknown_agg_prod_types = list(current_agg_pt_set - current_avail_aggreg_pt_set)
                if len(unknown_agg_prod_types) > 0:
                    errors_list.append(
                        f'Unknown/not available aggreg. prod. types {msg_suffix} {elt_country}:'
                        f' {unknown_agg_prod_types}')

        # check that both dates are in allowed period
        allowed_period_msg = (f'[{MIN_DATE_IN_DATA.strftime(DATE_FORMAT_IN_JSON)}, '
                              f'{MAX_DATE_IN_DATA.strftime(DATE_FORMAT_IN_JSON)}]')
        if not (MIN_DATE_IN_DATA <= self.uc_period_start <= MAX_DATE_IN_DATA):
            errors_list.append(
                f'UC period start {self.uc_period_start.strftime(DATE_FORMAT_IN_JSON)} not in '
                f'allowed period {allowed_period_msg}')
        if not (MIN_DATE_IN_DATA <= self.uc_period_end <= MAX_DATE_IN_DATA):
            errors_list.append(
                f'UC period end {self.uc_period_end.strftime(DATE_FORMAT_IN_JSON)} not in '
                f'allowed period {allowed_period_msg}')

        # updated fuel sources params -> check non-negative marginal cost and CO2 emission values
        if self.updated_fuel_sources_params is not None:
            for source, params in self.updated_fuel_sources_params.items():
                for name, val in params.items():
                    if val < 0:
                        errors_list.append(
                            f'Updated fuel source {source} param {name} must be non-negative; but value read {val}')

        # stop if any error
        if len(errors_list) > 0:
            uncoherent_param_stop(param_errors=errors_list)
        else:
            logging.info('Modified LONG-TERM UC PARAMETERS ARE COHERENT!')
            logging.info(f'SIMULATION CAN START on {str(self)}')

    def set_countries(self, countries: List[str]):
        self.selected_countries = countries

    def set_target_year(self, year: int):
        self.selected_target_year = year

    def set_climatic_year(self, climatic_year: int):
        self.selected_climatic_year = climatic_year

    def set_uc_period(self, start: Union[str, datetime] = None, end: Union[str, datetime] = None):
        if start is not None:
            self.uc_period_start = start
        if end is not None:
            self.uc_period_end = end


def overwrite_uc_run_params(uc_run_params: UCRunParams, uc_run_params_2: UCRunParams,
                            fields_tb_overwritten: List[str]) -> UCRunParams:
    uc_run_params_2_dict = uc_run_params_2.__dict__
    # keep only defined values
    keys_with_none_val = [key for key in fields_tb_overwritten if uc_run_params_2_dict[key] is None]
    if len(keys_with_none_val) > 0:
        logging.warning(f'The following attrs {keys_with_none_val} have None values '
                        f'-> will not be used to overwrite UCRunParams object')
    uc_run_params_2_dict = {key: val for key, val in uc_run_params_2_dict.items() if val is not None}

    for attr_name in fields_tb_overwritten:
        setattr(uc_run_params, attr_name, uc_run_params_2_dict[attr_name])
    return uc_run_params
