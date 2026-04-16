from dataclasses import dataclass

from common.constants.countries import set_country_trigram


@dataclass
class ProdTypeNames:  # by alpha. order
    batteries: str = 'batteries'
    biofuel: str = 'biofuel'
    coal: str = 'coal'
    csp_no_storage: str = 'csp_nostorage'
    demand_side_response: str = 'demand_side_response_capacity'  # TODO: why capa in this name?
    failure: str = 'failure'
    gas: str = 'gas'
    hard_coal: str = 'hard_coal'
    hydro_pondage: str = 'hydro_pondage'
    hydro_pump_storage_closed: str = 'hydro_pump_storage_closed_loop'
    hydro_pump_storage_open: str = 'hydro_pump_storage_open_loop'
    hydro_reservoir: str = 'hydro_reservoir'
    hydro_ror: str = 'hydro_run_of_river'
    lignite: str = 'lignite'
    nuclear: str = 'nuclear'
    oil: str = 'oil'
    others_non_renewable: str = 'others_non-renewable'  # TODO: with '_' instead of '-'? (TB tested)
    others_renewable: str = 'others_renewable'
    solar_pv: str = 'solar_pv'
    solar_thermal: str = 'solar_thermal'
    wind_offshore: str = 'wind_offshore'
    wind_onshore: str = 'wind_onshore'


STOCK_LIKE_PROD_TYPES = [ProdTypeNames.hydro_reservoir, ProdTypeNames.hydro_pump_storage_closed,
                         ProdTypeNames.hydro_pump_storage_open, ProdTypeNames.batteries,
                         ProdTypeNames.demand_side_response]


UNIT_NAME_SEP = '_'


def set_gen_unit_name(country: str, agg_prod_type: str) -> str:
    country_trigram = set_country_trigram(country=country)
    return f'{country_trigram}{UNIT_NAME_SEP}{agg_prod_type}'


def get_country_from_unit_name(prod_unit_name: str) -> str:
    return prod_unit_name.split(UNIT_NAME_SEP)[0]


def get_prod_type_from_unit_name(prod_unit_name: str) -> str:
    """
    ATTENTION tricky cases if '_' in prod type... the rule is to take the str after country name + separator
    Args:
        prod_unit_name:

    Returns:
    """
    country = get_country_from_unit_name(prod_unit_name=prod_unit_name)
    return prod_unit_name[len(country) + len(UNIT_NAME_SEP):]


STORAGE_COL_SUFFIX = {'prod': 'prod', 'cons': 'cons'}


def add_suffix_to_storage_unit_col(col: str, col_type: str) -> str:
    """
    Suffix added when both prod. and cons. for storage are put in a same df -> to distinguish the 2 columns
    for a same prod unit
    Args:
        col:
        col_type: either prod/cons

    Returns:

    """
    if col_type not in STORAGE_COL_SUFFIX:
        raise Exception(f'Suffix cannot be added to storage column {col}; unknown type {col_type} '
                        f'(it must be in {list(STORAGE_COL_SUFFIX)})')
    return col + UNIT_NAME_SEP + STORAGE_COL_SUFFIX[col_type]
