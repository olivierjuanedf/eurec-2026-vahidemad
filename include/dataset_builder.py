import os
import warnings
from itertools import product
from pathlib import Path
from datetime import datetime

import linopy.model
import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
import pypsa
import matplotlib.pyplot as plt

from common.constants.countries import set_country_trigram
from common.constants.optimisation import OptimSolvers, DEFAULT_OPTIM_SOLVER_PARAMS, SolverParams, \
    OptimPbCharacteristics, OptimPbTypes
from common.constants.prod_types import get_country_from_unit_name, ProdTypeNames
from common.constants.pypsa_params import GEN_UNITS_PYPSA_PARAMS
from common.error_msgs import print_errors_list
from common.fuel_sources import FuelSource
from common.long_term_uc_io import get_network_figure, FigNamesPrefix, get_output_figure
from include.uc_postprocessing import UCSummaryMetrics, UCOptimalSolution
from utils.basic_utils import (lexico_compar_str, rm_elts_with_none_val, rm_elts_in_str, sort_lexicographically,
                               format_with_spaces)
from utils.dir_utils import make_dir
from utils.pypsa_utils import get_network_obj_value
from utils.serializer import array_serializer


@dataclass
class GenerationUnitData:
    name: str
    type: str
    carrier: str = None
    p_nom: Union[float, np.ndarray] = None
    p_min_pu: Union[float, np.ndarray] = None
    p_max_pu: Union[float, np.ndarray] = None
    efficiency: float = None
    efficiency_store: float = None
    efficiency_dispatch: float = None
    marginal_cost: float = None
    committable: bool = False
    max_hours: float = None
    cyclic_state_of_charge: bool = None
    inflow: np.ndarray = None
    soc_min: np.ndarray = None
    soc_max: np.ndarray = None
    state_of_charge_initial: float = None

    def get_non_none_attr_names(self):
        return [key for key, val in self.__dict__.items() if val is not None]

    def serialize(self) -> dict:
        unit_data_dict = self.__dict__
        # (1d) nd array to list
        unit_data_dict = {key: array_serializer(my_array=val, stat_repres=True) if isinstance(val, np.ndarray) else val
                          for key, val in unit_data_dict.items()}
        return unit_data_dict


def select_gen_units_data(gen_units_data: List[GenerationUnitData], countries: List[str], 
                          unit_types: List[str]) -> List[GenerationUnitData]:
    return [elt for elt in gen_units_data
            if get_country_from_unit_name(elt.name) in countries and elt.type in unit_types]


GEN_UNITS_DATA_TYPE = Dict[str, List[GenerationUnitData]]
PYPSA_RESULT_TYPE = Tuple[str, str]


def check_gen_unit_params(params: dict, n_ts: int) -> bool:
    # check that max and min power pu are either constant or of the length of considered horizon
    for param_name in [GEN_UNITS_PYPSA_PARAMS.min_power_pu, GEN_UNITS_PYPSA_PARAMS.max_power_pu]:
        if param_name in params:
            param_value = params[param_name]
            if isinstance(param_value, list) or isinstance(param_value, np.ndarray):
                if not len(param_value) == n_ts:
                    return False
    return True


def set_per_bus_asset_msg(asset_names: List[str]):
    """
    List of {bus name}_{asset name} to be converted to more elegant msg
    """
    name_sep = '_'
    # get dict. gathering asset names per bus
    per_bus_assets = {}
    for full_name in asset_names:
        name_split = full_name.split(name_sep)
        bus_name = name_split[0]
        asset_name = name_sep.join(name_split[1:])
        if bus_name not in per_bus_assets:
            per_bus_assets[bus_name] = []
        per_bus_assets[bus_name].append(asset_name)
    # get log message with one line per bus
    per_bus_msg = ''
    for bus, assets in per_bus_assets.items():
        per_bus_msg += f'\n- {bus}: {assets}'
    return per_bus_msg


def set_per_origin_bus_links_msg(link_names: List[str]) -> str:
    link_sep = '-'
    links_msg = ''
    n_links = len(link_names)
    i_link = 0
    while i_link < n_links:
        common_origin_links = [link_names[i_link]]
        origin = link_names[i_link].split(link_sep)[0]
        j = 1
        while i_link + j < n_links:
            current_origin = link_names[i_link + j].split(link_sep)[0]
            if current_origin == origin:
                common_origin_links.append(link_names[i_link + j])
                j += 1
            else:
                break
        links_msg += f'\n- from {origin}: {[tuple(elt_link.split(link_sep)) for elt_link in common_origin_links]}'
        i_link += j
    return links_msg


def set_optim_pb_type(model: linopy.model.Model) -> Optional[str]:
    if model.is_linear:
        if len(model.integers) > 0:
            return OptimPbTypes.milp
        else:
            return OptimPbTypes.lp
    # quadratic if not linear (or other possibilities?)
    if model.is_quadratic:
        if len(model.integers) > 0:
            return OptimPbTypes.miqp
        else:
            return OptimPbTypes.qp
    return None


@dataclass
class PypsaModel:
    # TODO: json dump to have an aggreg. view of such a model in saved files (and check stress test effect rapidly)
    name: str
    network: pypsa.Network = None
    uc_summary_metrics: UCSummaryMetrics = None  # UC summary metrics (ENS, nber of failure hours, costs...)
    optim_solver_params: SolverParams = None
    DEFAULT_CARRIER = 'ac'

    def init_pypsa_network(self, date_idx: pd.Index, date_range: pd.DatetimeIndex = None):
        logging.info('Initialize PyPSA network')
        self.network = pypsa.Network(name=self.name, snapshots=date_idx)
        if date_range is not None:
            self.network.set_snapshots(date_range[:-1])

    def add_gps_coordinates(self, countries_gps_coords: Dict[str, Tuple[float, float]], carrier_name: str = None):
        if carrier_name is None:
            carrier_name = self.DEFAULT_CARRIER

        logging.info('Add GPS coordinates')
        for country, gps_coords in countries_gps_coords.items():
            country_bus_name = get_country_bus_name(country=country)
            self.network.add(GEN_UNITS_PYPSA_PARAMS.bus.capitalize(), name=f'{country_bus_name}',
                             x=gps_coords[0], y=gps_coords[1], carrier=carrier_name)

    def add_energy_carriers(self, fuel_sources: Dict[str, FuelSource]):
        logging.info('Add energy carriers')
        for carrier in list(fuel_sources.keys()):
            self.network.add(GEN_UNITS_PYPSA_PARAMS.carrier.capitalize(), name=carrier,
                             co2_emissions=fuel_sources[carrier].co2_emissions / 1000)

    def add_per_bus_energy_carriers(self, fuel_sources: Dict[str, FuelSource], carrier_name: str = None):
        if carrier_name is None:
            carrier_name = self.DEFAULT_CARRIER
        all_bus_names = self.get_bus_names()
        logging.info(f'Add per-bus energy carriers for: {all_bus_names}')
        for bus_name in all_bus_names:
            self.network.add(GEN_UNITS_PYPSA_PARAMS.carrier.capitalize(), name=bus_name,
                             co2_emissions=fuel_sources[carrier_name].co2_emissions / 1000)

    def add_generators(self, generators_data: Dict[str, List[GenerationUnitData]]):
        logging.info('Add generators - associated to their respective buses')
        for country, gen_units_data in generators_data.items():
            country_bus_name = get_country_bus_name(country=country)
            for gen_unit_data in gen_units_data:
                pypsa_gen_unit_dict = gen_unit_data.__dict__
                # remove elements with None values, as all attrs were listed in this dict.
                pypsa_gen_unit_dict = rm_elts_with_none_val(my_dict=pypsa_gen_unit_dict)
                logging.debug(f'{country}, {pypsa_gen_unit_dict}')
                params_ok = check_gen_unit_params(params=pypsa_gen_unit_dict, n_ts=len(self.network.snapshots))
                if not params_ok:
                    logging.warning(f'Pb with generator parameters {pypsa_gen_unit_dict} '
                                    f'\n-> generator not added to the PyPSA model')
                    continue

                # case of storage units, identified via the presence of max_hours param
                if pypsa_gen_unit_dict.get(GEN_UNITS_PYPSA_PARAMS.max_hours, None) is not None:
                    if pypsa_gen_unit_dict.get(GEN_UNITS_PYPSA_PARAMS.soc_init, None) is None:
                        # initial SoC fixed to 80% statically here
                        logging.info(f'Default value set for {pypsa_gen_unit_dict[GEN_UNITS_PYPSA_PARAMS.name]} init. SOC as 80% of energy storage capa.')
                        init_soc = (pypsa_gen_unit_dict[GEN_UNITS_PYPSA_PARAMS.power_capa]
                                    * pypsa_gen_unit_dict[GEN_UNITS_PYPSA_PARAMS.max_hours] * 0.8)
                        pypsa_gen_unit_dict[GEN_UNITS_PYPSA_PARAMS.soc_init] = init_soc
                    self.network.add('StorageUnit', bus=f'{country_bus_name}', **pypsa_gen_unit_dict)
                else:
                    self.network.add('Generator', bus=f'{country_bus_name}', **pypsa_gen_unit_dict)
        generator_names = self.get_generator_names()
        logging.info(f'Considered generators ({len(generator_names)}): '
                     f'{set_per_bus_asset_msg(asset_names=generator_names)}')
        storage_unit_names = self.get_storage_unit_names()
        logging.info(f'Considered storage units ({len(storage_unit_names)}): '
                     f'{set_per_bus_asset_msg(asset_names=storage_unit_names)}')

    def add_loads(self, demand: Dict[str, pd.DataFrame], carrier_name: str = None):
        if carrier_name is None:
            carrier_name = self.DEFAULT_CARRIER
        logging.info('Add loads - associated to their respective buses')
        for country in demand:
            country_bus_name = get_country_bus_name(country=country)
            load_data = {GEN_UNITS_PYPSA_PARAMS.name: f'{country_bus_name}-load',
                         GEN_UNITS_PYPSA_PARAMS.bus: f'{country_bus_name}',
                         GEN_UNITS_PYPSA_PARAMS.carrier: carrier_name,
                         GEN_UNITS_PYPSA_PARAMS.set_power: demand[country]['value'].values}
            self.network.add('Load', **load_data)

    def add_interco_links(self, countries: List[str], interco_capas: Dict[Tuple[str, str], float],
                          carrier_name: str = None):
        if carrier_name is None:
            carrier_name = self.DEFAULT_CARRIER

        logging.info(f'Add interco. links - between the selected countries: {countries}')
        links = []
        symmetric_links = []
        links_wo_capa_msg = []
        for country_origin, country_dest in product(countries, countries):
            link_tuple = (country_origin, country_dest)
            # do not add link for (country, country); neither for symmetric links already treated 
            # (as bidirectional setting p_min_pu=-1)
            if not country_origin == country_dest and link_tuple not in symmetric_links:
                # TODO: fix AC/DC.... all AC here in names but not true (cf. CS students data)
                current_interco_capa, is_sym_interco = \
                    get_current_interco_capa(interco_capas=interco_capas, country_origin=country_origin,
                                             country_dest=country_dest)
                if current_interco_capa is None:
                    # if symmetrical interco order lexicographically to fit with input data format
                    if is_sym_interco:
                        link_wo_capa = lexico_compar_str(string1=country_origin,
                                                         string2=country_dest, return_tuple=True)
                    else:
                        link_wo_capa = link_tuple
                    link_wo_capa_msg = f'({link_wo_capa[0]}, {link_wo_capa[1]})'
                    if link_wo_capa_msg not in links_wo_capa_msg:
                        links_wo_capa_msg.append(f'({link_wo_capa[0]}, {link_wo_capa[1]})')
                else:
                    country_origin_bus_name = get_country_bus_name(country=country_origin)
                    country_dest_bus_name = get_country_bus_name(country=country_dest)
                    if is_sym_interco:
                        p_min_pu, p_max_pu = -1, 1
                        symmetric_links.append(link_tuple)
                    else:
                        p_min_pu, p_max_pu = 0, 1
                    links.append({GEN_UNITS_PYPSA_PARAMS.name:
                                      f'{country_origin_bus_name}-{country_dest_bus_name}_{carrier_name}',
                                  f'{GEN_UNITS_PYPSA_PARAMS.bus}0': country_origin_bus_name,
                                  f'{GEN_UNITS_PYPSA_PARAMS.bus}1': country_dest_bus_name,
                                  GEN_UNITS_PYPSA_PARAMS.nominal_power: current_interco_capa,
                                  GEN_UNITS_PYPSA_PARAMS.min_power_pu: p_min_pu,
                                  GEN_UNITS_PYPSA_PARAMS.max_power_pu: p_max_pu,
                                  GEN_UNITS_PYPSA_PARAMS.carrier: carrier_name}
                                 )
        if len(links_wo_capa_msg) > 0:
            print_errors_list(error_name='-> interco. links without capacity data', errors_list=links_wo_capa_msg)

        # add to PyPSA network
        for link in links:
            if link[GEN_UNITS_PYPSA_PARAMS.power_capa] > 0:
                self.network.add('Link', **link)
        link_names = self.get_link_names()
        logging.info(f'Considered links - the ones with nonzero capacity ({len(link_names)}), in alphabetic order '
                     f'of origin: {set_per_origin_bus_links_msg(link_names=link_names)}')

    def build_model_before_adding_custom_const(self):
        logging.warning('In PyPSA 0.35.1 not possible to build only model without solving it; '
                        'to add custome constraints it will be solved first "for fun" (ignoring the solution)')
        # TODO: see if deactivate resolution logs, in cmd windows/log file
        self.network.optimize(build_only=True, solver_options={'logfile': '/dev/null'})

    def add_sum_of_prod_custom_const(self):
        """
        Add sum-of-production custom constraints, of the form sum_{z, t} coeff(z, t) * production(z, t) <= ub (or >=, =)
        N.B. Can be applied to CO2 max emission constraints
        Returns:
        """
        logging.warning(f'Add custom sum of prod constraints (sum over z,t coeff(z,t) * prod(z, t) <= ub, or >=, =; '
                        f'used, e.g. for max CO2 emissions) -> to be coded')

    def add_hydro_extreme_levels_constraint(self, soc_min: Dict[str, np.ndarray], soc_max: Dict[str, np.ndarray], 
                                            energy_capa: Dict[str, np.ndarray]):
        """
        Add constraint on hydro extreme SOC levels
        :param soc_min: dict {unit name: soc min vector}
        :param soc_max: idem, max
        :param energy_capa: dict {unit name: energy capa value}
        """
        bob = 1
        # check if soc_min/max values induce a real constraint (not all 0/bigger than energy capacity)
        # TODO: loop over bus?
        # hydro_soc = self.network.model.variables[PypsaOptimVarNames.storage_soc]["battery"]
        # self.network.model.add_constraints(hydro_soc >= soc_min_profile.values, name="soc_min")
        # self.network.model.add_constraints(hydro_soc <= soc_max_profile.values, name="soc_max")
    
    def add_hydro_extreme_gen_constraint(self):
        bob = 1
        # # Generator production constraints
        # gen_p = m.variables["Generator-p"]["gen"]
        # m.add_constraints(gen_p >= gen_min_profile.values, name="gen_min")
        # m.add_constraints(gen_p <= gen_max_profile.values, name="gen_max")

    def get_bus_names(self) -> List[str]:
        return list(set(self.network.buses.index))

    def get_generator_names(self) -> List[str]:
        return list(self.network.generators.index)

    def get_storage_unit_names(self) -> List[str]:
        return list(self.network.storage_units.index)

    def get_link_names(self, only_links_with_nonzero_capa: bool = True, rm_carrier_name: bool = True,
                       lexico_sort: bool = True) -> List[str]:
        df_links = self.network.links
        if only_links_with_nonzero_capa:
            df_links = df_links[df_links[GEN_UNITS_PYPSA_PARAMS.nominal_power] > 0]
        link_names = list(df_links.index)
        if rm_carrier_name:
            link_names = [rm_elts_in_str(my_str=full_link_name, elts_tb_removed=['_ac', '_dc'])
                          for full_link_name in link_names]
        if lexico_sort:
            link_names = sort_lexicographically(strings=link_names)
        return link_names

    def get_per_bus_total_installed_capa(self):
        bus_names = self.get_bus_names()
        df_generators = self.network.generators
        return {name: df_generators.loc[(df_generators.index.str.startswith(f'{name}-'))
                                        & (df_generators['type'] != ProdTypeNames.failure), 'p_nom'].sum()
                for name in bus_names}

    def get_per_bus_max_load(self) -> Dict[str, float]:
        bus_names = self.get_bus_names()
        return {name: max(self.network.loads_t['p_set'][f'{name}-load']) for name in bus_names}

    def plot_network(self, toy_model_output: bool = False, country: str = None):
        # catch DeprecationWarnings TODO: fix/more robust way to catch them?
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.network.plot(title=f'{self.name.capitalize()} PyPSA network', color_geomap=True, jitter=0.3)
            plt.savefig(get_network_figure(toy_model_output=toy_model_output, country=country,
                                           n_bus=len(self.network.buses)))
            plt.close()

    def set_default_optim_solver(self, warning_msg: str):
        msg_default_solver_used = f'-> default {DEFAULT_OPTIM_SOLVER_PARAMS.name} will be used instead'
        logging.warning(f'{warning_msg} {msg_default_solver_used}')
        self.optim_solver_params = DEFAULT_OPTIM_SOLVER_PARAMS

    def set_optim_solver(self, solver_params: SolverParams = None):
        # if no solver provided in arg. -> set default one
        if solver_params is None:
            self.optim_solver_params = DEFAULT_OPTIM_SOLVER_PARAMS
        # else check if coherent parameters; otherwise set default solver
        else:
            all_solver_names = OptimSolvers.__dict__.values()
            solver_name = solver_params.name
            if solver_name not in all_solver_names:
                warning_msg = f'Solver name {solver_name} not in allowed list {all_solver_names}'
                self.set_default_optim_solver(warning_msg=warning_msg)
            else:
                self.optim_solver_params = solver_params
            if not self.optim_solver_params.name == DEFAULT_OPTIM_SOLVER_PARAMS.name:
                # check that license file param is defined
                solver_license_file = self.optim_solver_params.license_file
                if solver_license_file is None:
                    warning_msg = f'Licence file for optim. solver {self.optim_solver_params.name} not provided'
                    self.set_default_optim_solver(warning_msg=warning_msg)
                else:
                    # license file must be at root of the project
                    if not os.path.exists(path=solver_license_file):
                        warning_msg = f'Licence file {solver_license_file} does not exist (at root of project)'
                        self.set_default_optim_solver(warning_msg=warning_msg)
                    else:
                        os.environ[f'{self.optim_solver_params.name.upper()}_LICENSE_FILE'] = solver_license_file

    def get_optim_pb_characteristics(self) -> OptimPbCharacteristics:
        """
        N.B. (i) This method can be called only after having optimized network in PyPSA 0.35.1 (model attribute of network
        not init before that)
        (ii) network.model.constraints contains per type of constraint info (dimensions and size)
        """
        linopy_model = self.network.model
        return OptimPbCharacteristics(type=set_optim_pb_type(model=linopy_model),
                                      n_variables=len(linopy_model.variables.flat),
                                      n_int_variables=len(linopy_model.integers),
                                      n_constraints=len(linopy_model.constraints.flat))

    def optimize_network(self, year: int, n_countries: int, period_start: datetime, save_lp_file: bool = True,
                         toy_model_output: bool = False, countries: List[str] = None) -> PYPSA_RESULT_TYPE:
        """
        Solve the optimization UC problem associated to current network
        :returns a tuple (xxx, status of resolution)
        """
        logging.info('Optimise "network" - i.e. solve associated UC problem')
        result = self.network.optimize(solver_name=self.optim_solver_params.name)
        logging.info(f'Obtained result: {result}')
        if save_lp_file:
            save_lp_model(self.network, year=year, n_countries=n_countries, period_start=period_start,
                          toy_model_output=toy_model_output, countries=countries)
        return result

    def set_uc_opt_solution(self) -> UCOptimalSolution:
        """
        Returns: an object containing variables + methods on the UC optimal solution
        """
        # init.
        uc_opt_solution = UCOptimalSolution(network_name=self.network.name)
        # get primal optimal values from PyPSA network
        uc_opt_solution.get_prod_var_opt(network=self.network)
        uc_opt_solution.get_storage_vars_opt(network=self.network)
        uc_opt_solution.get_link_flow_vars_opt(network=self.network)
        # and dual variables - some of them "entering" into Linopy framework
        uc_opt_solution.get_sde_dual_var_opt(network=self.network)
        uc_opt_solution.get_link_capa_dual_var_opt(network=self.network)
        return uc_opt_solution

    def get_opt_value(self, pypsa_resol_status: str) -> float:
        objective_value = get_network_obj_value(network=self.network)
        objective_value_refmted = format_with_spaces(number=int(objective_value/1e6))
        logging.info(
            f'Optimisation resolution status is {pypsa_resol_status} with objective value (cost) = '
            f'{objective_value_refmted} (M€) -> output data (resp. figures) can be generated')
        return objective_value

    def plot_installed_capas(self, country: str, year: int, toy_model_output: bool = False):
        country_trigram = set_country_trigram(country=country)
        # catch DeprecationWarnings TODO: fix/more robust way to catch them?
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            # N.B. p_nom_opt is the optimized capacity (that can be also a variable in PyPSA but here...
            # not optimized - only UC problem -> values plotted correspond to the ones that can be found in input data)
            # all but failure asset capacity will be used in plot
            self.network.generators.p_nom_opt.drop(f'{country_trigram}_failure').div(1e3).plot.bar(ylabel='GW',
                                                                                                   figsize=(8, 3))
            plt.tight_layout()
            plt.savefig(get_output_figure(fig_name=FigNamesPrefix.capacity, country=country, year=year,
                                          toy_model_output=toy_model_output))
            plt.close()


# def overwrite_gen_units_fuel_src_params(generation_units_data: GEN_UNITS_DATA_TYPE, updated_fuel_sources_params: Dict[
#     str, Dict[str, float]]) -> GEN_UNITS_DATA_TYPE:
#     for _, units_data in generation_units_data.items():
#         # loop over all units in current country
#         for indiv_unit_data in units_data:
#             current_prod_type = get_prod_type_from_unit_name(prod_unit_name=indiv_unit_data.name)
#             if current_prod_type in updated_fuel_sources_params:
#                 # TODO: add CO2 emissions, and merge both case? Q2OJ: how-to properly?
#                 if GEN_UNITS_PYPSA_PARAMS.marginal_cost in updated_fuel_sources_params[current_prod_type]:
#                     indiv_unit_data.marginal_cost = updated_fuel_sources_params[current_prod_type][
#                         GEN_UNITS_PYPSA_PARAMS.marginal_cost]
#
#         # TODO: from units data info on fuel source extract and apply updated params values
#         updated_fuel_sources_params = None


def get_country_bus_name(country: str) -> str:
    return country.lower()[:3]


STORAGE_LIKE_UNITS = ['batteries', 'flexibility', 'hydro']


# TODO: suppr?
# def add_loads(network, demand: Dict[str, pd.DataFrame]):
#     print("Add loads - associated to their respective buses")
#     for country in demand:
#         country_bus_name = get_country_bus_name(country=country)
#         load_data = {"name": f"{country_bus_name}-load", "bus": f"{country_bus_name}",
#                      "carrier": "AC", "p_set": demand[country]["value"].values}
#         network.add("Load", **load_data)
#     return network


def get_current_interco_capa(interco_capas: Dict[Tuple[str, str], float], country_origin: str,
                             country_dest: str) -> Tuple[Optional[float], Optional[bool]]:
    link_tuple = (country_origin, country_dest)
    reverse_link_tuple = (country_dest, country_origin)
    if link_tuple in interco_capas:
        current_interco_capa = interco_capas[link_tuple]
        is_sym_interco = reverse_link_tuple not in interco_capas
    elif reverse_link_tuple in interco_capas:
        current_interco_capa = interco_capas[reverse_link_tuple]
        is_sym_interco = True
    else:
        current_interco_capa = None
        is_sym_interco = None
    return current_interco_capa, is_sym_interco


def set_period_start_file(year: int, period_start: datetime) -> str:
    return datetime(year=year, month=period_start.month, day=period_start.day).strftime('%Y-%m-%d')


def save_lp_model(network: pypsa.Network, year: int, period_start: datetime, countries: List[str] = None,
                  n_countries: int = None, add_random_suffix: bool = False, toy_model_output: bool = False):
    import pypsa.optimization as opt
    from common.long_term_uc_io import set_full_lt_uc_output_folder, OutputFolderNames

    m = opt.create_model(network)

    # set prefix
    n_countries_max_in_prefix = 3
    if countries is not None:
        if len(countries) <= n_countries_max_in_prefix:
            prefix = '-'.join(countries)
            n_countries = None
        else:
            n_countries = len(countries)
    if n_countries is not None:
        prefix = '1-country' if n_countries == 1 else f'{n_countries}-countries'

    # to avoid suppressing previous runs results
    if add_random_suffix:
        run_id = np.random.randint(99)
        random_suffix = f'_{run_id}'
    else:
        random_suffix = ''

    period_start_file = set_period_start_file(year=year, period_start=period_start)
    file_suffix = f'{prefix}_{period_start_file}{random_suffix}'
    # if more than 1 country lp will be saved in a europe output folder (not monozone_{country})
    country_output_folder = countries[0] if countries is not None and len(countries) == 1 else None
    output_folder_data = set_full_lt_uc_output_folder(folder_type=OutputFolderNames.data, country=country_output_folder,
                                                      toy_model_output=toy_model_output)
    make_dir(full_path=output_folder_data)
    lp_filepath = f'{output_folder_data}/model_{file_suffix}.lp'
    logging.info(f'Save model in .lp file: {lp_filepath}')
    m.to_file(Path(lp_filepath))
