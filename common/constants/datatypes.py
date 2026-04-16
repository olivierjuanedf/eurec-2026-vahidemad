from dataclasses import dataclass

from common.constants.prod_types import ProdTypeNames


@dataclass
class DatatypesNames:
    capa_factor: str = 'res_capa-factors'
    demand: str = 'demand'
    installed_capa: str = 'generation_capas'
    interco_capa: str = 'intercos_capas'
    net_demand: str = 'net_demand'  # not primary datatypes, obtain from preceding ones
    fatal_production: str = 'fatal_production'  # idem
    # different hydro (sub)datatypes
    hydro_ror: str = 'hydro_run_of_river'
    hydro_inflows: str = 'hydro_inflows'
    hydro_levels_min: str = 'hydro_levels_min'
    hydro_levels_max: str = 'hydro_levels_max'


DATATYPE_NAMES = DatatypesNames()
HYDRO_DTS = [DatatypesNames.hydro_ror, DatatypesNames.hydro_inflows,
             DatatypesNames.hydro_levels_min, DatatypesNames.hydro_levels_max]
PROD_TYPES_PER_DT = {DATATYPE_NAMES.capa_factor: 
                     [ProdTypeNames.csp_no_storage, ProdTypeNames.solar_pv, ProdTypeNames.wind_offshore,
                      ProdTypeNames.wind_onshore],
                     DATATYPE_NAMES.installed_capa: 
                     [ProdTypeNames.batteries, ProdTypeNames.biofuel, ProdTypeNames.coal, ProdTypeNames.hard_coal,
                      ProdTypeNames.lignite, ProdTypeNames.demand_side_response, ProdTypeNames.gas,
                      ProdTypeNames.hydro_pondage, ProdTypeNames.hydro_pump_storage_closed,
                      ProdTypeNames.hydro_pump_storage_open, ProdTypeNames.hydro_reservoir,
                      ProdTypeNames.hydro_ror, ProdTypeNames.nuclear, ProdTypeNames.oil,
                      ProdTypeNames.solar_pv, ProdTypeNames.solar_thermal,
                      ProdTypeNames.wind_offshore, ProdTypeNames.wind_onshore]
                      }
UNITS_PER_DT = {DATATYPE_NAMES.demand: 'mw', DATATYPE_NAMES.fatal_production: 'mw', DATATYPE_NAMES.net_demand: 'mw',
                DATATYPE_NAMES.capa_factor: '%', DATATYPE_NAMES.installed_capa: 'mw', DATATYPE_NAMES.interco_capa: 'mw'}
PLOT_YLABEL_PER_DT = {DATATYPE_NAMES.demand: 'Demand', DATATYPE_NAMES.fatal_production: '(Fatal) Production',
                      DATATYPE_NAMES.net_demand: 'Net demand', DATATYPE_NAMES.capa_factor: 'RES capa-factors',
                      DATATYPE_NAMES.installed_capa: 'Generation capas', DATATYPE_NAMES.interco_capa: 'Intercos capas'}
