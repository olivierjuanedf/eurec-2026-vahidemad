from dataclasses import dataclass

from utils.type_checker import CheckerNames


@dataclass
class CountryJsonParamNames:
    capacities_tb_overwritten: str = 'capacities_tb_overwritten'
    selected_prod_types: str = 'selected_prod_types'
    team: str = 'team'


@dataclass
class EuropeJsonParamNames:
    extra_params: str = 'extra_params'
    failure_penalty: str = 'failure_penalty'
    failure_power_capa: str = 'failure_power_capa'
    interco_capas_tb_overwritten: str = 'interco_capas_tb_overwritten'
    selected_climatic_year: str = 'selected_climatic_year'
    selected_countries: str = 'selected_countries'
    selected_target_year: str = 'selected_target_year'
    uc_period_end: str = 'uc_period_end'
    uc_period_start: str = 'uc_period_start'


@dataclass
class EuropeJsonExtraParamNames:
    co2_emis_price: str = 'co2_emis_price'
    max_co2_emis: str = 'max_co2_emis_constraints'


ALL_KEYWORD = 'all'
OPTIONAL_EUR_JSON_PARAMS = [EuropeJsonParamNames.extra_params]
EUR_JSON_PARAM_TYPES_FOR_CHECK = {EuropeJsonParamNames.extra_params: CheckerNames.is_dict,
                                  EuropeJsonParamNames.failure_penalty: CheckerNames.is_float,
                                  EuropeJsonParamNames.failure_power_capa: CheckerNames.is_float,
                                  EuropeJsonParamNames.interco_capas_tb_overwritten: CheckerNames.is_dict_str_int,
                                  EuropeJsonParamNames.selected_climatic_year: CheckerNames.is_int,
                                  EuropeJsonParamNames.selected_target_year: CheckerNames.is_int,
                                  EuropeJsonParamNames.uc_period_end: CheckerNames.is_str,
                                  EuropeJsonParamNames.uc_period_start: CheckerNames.is_str}
