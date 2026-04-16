from dataclasses import dataclass


@dataclass
class ERAAParamNames:
    energy_capacity: str = 'energy_capacity'
    # generic term for power capacity -> e.g., for thermal assets
    power_capacity: str = 'power_capacity'
    # turbine/pump max power capacities -> used for hydro assets
    power_capacity_turbine: str = 'power_capacity_turbine'
    power_capacity_pumping: str = 'power_capacity_pumping'
    # idem, but for stock assets - with different terminology in ERAA data
    power_capacity_injection: str = 'power_capacity_injection'
    power_capacity_offtake: str = 'power_capacity_offtake'
