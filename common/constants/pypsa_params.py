from dataclasses import dataclass


@dataclass
class GenUnitsPypsaParams:
    bus: str = 'bus'
    carrier: str = 'carrier'
    capa_factors: str = 'p_max_pu'
    committable: str = 'committable'
    co2_emissions: str = 'co2_emissions'  # TODO: check that aligned on PyPSA generators attribute names
    efficiency: str = 'efficiency'
    efficiency_store: str = 'efficiency_store'  # if store/discharge efficiency to be distinguished, e.g. for stocks
    efficiency_dispatch: str = 'efficiency_dispatch'
    energy_capa: str = None
    inflow: str = 'inflow'
    marginal_cost: str = 'marginal_cost'
    max_hours: str = 'max_hours'
    max_power_pu: str = 'p_max_pu'
    min_power_pu: str = 'p_min_pu'
    name: str = 'name'
    nominal_power: str = 'p_nom'
    power_capa: str = 'p_nom'
    soc_init: float = 'state_of_charge_initial'
    set_power: str = 'p_set'


GEN_UNITS_PYPSA_PARAMS = GenUnitsPypsaParams()


@dataclass
class GenUnitsCustomParams:
    soc_min: str = 'soc_min'
    soc_max: str = 'soc_max'
    

@dataclass
class PypsaOptimVarNames:
    # related to generators
    generators_p: str = 'Generator-p'
    # related to storage units
    storage_p_dispatch: str = 'StorageUnit-p_dispatch'
    storage_p_store: str = 'StorageUnit-p_store'
    storage_soc: str = 'StorageUnit-state_of_charge'
    storage_spill: str = 'StorageUnit-spill'
    # related to links
    links_p: str = 'Link-p'
    