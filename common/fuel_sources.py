from dataclasses import dataclass
from typing import Dict

from common.long_term_uc_io import get_json_fuel_sources_file
from utils.read import check_and_load_json_file

"""
**[Optional, for better parametrization of assets]**
"""


@dataclass
class FuelNames:
    biomass: str = 'biomass'
    coal: str = 'coal'
    gas: str = 'gas'
    hydro: str = 'hydro'
    oil: str = 'oil'
    other_non_renewables: str = 'other_non_renew'
    other_renewables: str = 'other_renew'
    solar: str = 'solar'
    uranium: str = 'uranium'
    wind: str = 'wind'


@dataclass
class DummyFuelNames:
    ac: str = 'ac'
    dc: str = 'dc'


@dataclass
class FuelSource:
    name: str
    co2_emissions: float
    committable: bool = None
    energy_density_per_ton: float = None  # in MWh / ton
    cost_per_ton: float = None
    primary_cost: float = None  # € / MWh (multiply this by the efficiency of your power plant to get the marginal cost)

    # [Coding trick] this function will be applied automatically at initialization of an object of this class
    def __post_init__(self):
        if self.cost_per_ton is None or self.energy_density_per_ton is None:
            self.primary_cost = None
        elif self.energy_density_per_ton != 0:
            self.primary_cost = self.cost_per_ton / self.energy_density_per_ton
        else:
            self.primary_cost = 0


def add_other_sources(fuel_sources: Dict[str, FuelSource]) -> Dict[str, FuelSource]:
    source_matching = {FuelNames.other_renewables: FuelNames.biomass, FuelNames.other_non_renewables: FuelNames.oil}
    matched_params = ['co2_emissions', 'committable', 'energy_density_per_ton', 'cost_per_ton']
    for name, matched_name in source_matching.items():
        fs_params = [name.capitalize()]
        current_matched_params = fuel_sources[matched_name].__dict__
        fs_params.extend([current_matched_params[elt] for elt in matched_params])
        fuel_sources[name] = FuelSource(*fs_params)
    return fuel_sources


def set_fuel_sources_from_json(add_other_fs: bool = True) -> Dict[str, FuelSource]:
    filepath = get_json_fuel_sources_file()
    fuel_sources_data = check_and_load_json_file(json_file=filepath, file_descr='JSON fuel sources params')
    fuel_sources = {}
    for fuel_name, param_vals in fuel_sources_data.items():
        param_vals |= {'name': fuel_name.capitalize()}
        fuel_sources[fuel_name] = FuelSource(**param_vals)
    if add_other_fs:
        fuel_sources = add_other_sources(fuel_sources=fuel_sources)
    return fuel_sources


# to have carriers defined for all prod units in PyPSA
# TODO: make code ok without dummy CO2 emission values
dummy_co2_emissions = 0
DUMMY_FUEL_SOURCES = {DummyFuelNames.ac: FuelSource(DummyFuelNames.ac.capitalize(), dummy_co2_emissions),
                      DummyFuelNames.dc: FuelSource(DummyFuelNames.dc.capitalize(), dummy_co2_emissions)
                      }
