import logging
import os.path
from typing import Dict, Tuple, List, Optional

import pandas as pd
import time
from datetime import datetime

from common.constants.datadims import DataDimensions
from common.constants.extract_eraa_data import ERAADatasetDescr
from common.constants.optimisation import OPTIM_RESOL_STATUS, DEFAULT_OPTIM_SOLVER_PARAMS, SolverParams
from common.constants.plots import PlotNames
from common.constants.usage_params_json import EnvPhaseNames
from common.error_msgs import infeas_debugging_hints_msg
from common.fuel_sources import set_fuel_sources_from_json, DUMMY_FUEL_SOURCES, FuelSource
from common.logger import init_logger, stop_logger, deactivate_verbose_warnings, TITLE_LOG_SEP
from common.long_term_uc_io import set_full_lt_uc_output_folder
from common.plot_params import PlotParamsKeysInJson
from common.uc_run_params import UCRunParams
from include.dataset import Dataset
from include.dataset_builder import PypsaModel
from include.uc_postprocessing import UCSummaryMetrics
from include_runner.overwrite_uc_run_params import apply_fixed_uc_run_params
from utils.basic_utils import print_non_default
from utils.dates import get_period_str
from utils.read import (read_and_check_uc_run_params, read_and_check_pypsa_static_params,
                        read_given_phase_specific_key_from_plot_params,
                        read_plot_params, read_usage_params, read_solver_params)


def get_needed_eraa_data(uc_run_params: UCRunParams, eraa_data_descr: ERAADatasetDescr,
                         debug_mode: bool = False, debug_output_folder: str = None) -> Dataset:
    """
    Get ERAA data which is needed for current UC simulation; extracted from the data folder of this project
    :param uc_run_params
    :param eraa_data_descr
    :param debug_mode: to save some intermediate data in (JSON) files to more easily debug
    :param debug_output_folder: in which intermediate data must be saved
    """
    logging.info(f'{TITLE_LOG_SEP} II)1) Read needed ERAA ({eraa_data_descr.eraa_edition}) data {TITLE_LOG_SEP}')
    uc_period_msg = get_period_str(period_start=uc_run_params.uc_period_start,
                                   period_end=uc_run_params.uc_period_end)
    logging.info(f'For year (resp. climatic year) {uc_run_params.selected_target_year} '
                 f'(resp. {uc_run_params.selected_climatic_year}) and period {uc_period_msg}')
    # initialize dataset object
    eraa_dataset = Dataset(source=f'eraa_{eraa_data_descr.eraa_edition}',
                           agg_prod_types_with_cf_data=eraa_data_descr.agg_prod_types_with_cf_data,
                           is_stress_test=uc_run_params.is_stress_test)

    eraa_dataset.get_countries_data(uc_run_params=uc_run_params,
                                    aggreg_prod_types_def=eraa_data_descr.aggreg_prod_types_def)
    eraa_dataset.complete_data()
    logging.info(f'{TITLE_LOG_SEP} II)2) Check data coherence {TITLE_LOG_SEP}')
    logging.info('Get generation units data, from both ERAA data - read just before '
                 '- and complementary JSON parameter files')
    (eraa_dataset
     .get_generation_units_data(uc_run_params=uc_run_params,
                                pypsa_unit_params_per_agg_pt=eraa_data_descr.pypsa_unit_params_per_agg_pt,
                                units_complem_params_per_agg_pt=eraa_data_descr.units_complem_params_per_agg_pt)
     )

    # set 'committable' attribute to False, i.e. no 'dynamic constraints' modeled in the considered modeled
    eraa_dataset.set_committable_param_to_false()

    if debug_mode:
        gen_units_data_json = os.path.join(debug_output_folder, 'pypsa_gen_units_data.json')
        eraa_dataset.dump_gen_units_data_to_json(filepath=gen_units_data_json)

    return eraa_dataset


def check_min_pypsa_params_provided(eraa_dataset: Dataset):
    logging.info('Check that "minimal" PyPSA parameters for unit creation have been provided '
                 '(in JSON files) / read (from ERAA data)')
    pypsa_static_params = read_and_check_pypsa_static_params()
    eraa_dataset.control_min_pypsa_params_per_gen_units(
        pypsa_min_unit_params_per_agg_pt=pypsa_static_params.min_unit_params_per_agg_pt)


def create_pypsa_network_model(name: str, uc_run_params: UCRunParams, eraa_dataset: Dataset,
                               zones_gps_coords: Dict[str, Tuple[float, float]],
                               fuel_sources: Dict[str, FuelSource]) -> PypsaModel:
    logging.info(f'{TITLE_LOG_SEP} III) Create PyPSA UC model {TITLE_LOG_SEP}')
    pypsa_model = PypsaModel(name=name)
    date_idx = eraa_dataset.demand[uc_run_params.selected_countries[0]].index
    horizon = pd.date_range(
        start=uc_run_params.uc_period_start.replace(year=uc_run_params.selected_target_year),
        end=uc_run_params.uc_period_end.replace(year=uc_run_params.selected_target_year),
        freq='h'
    )
    pypsa_model.init_pypsa_network(date_idx=date_idx, date_range=horizon)
    # add GPS coordinates
    selec_countries_gps_coords = \
        {country: gps_coords for country, gps_coords in zones_gps_coords.items()
         if country in uc_run_params.selected_countries}
    pypsa_model.add_gps_coordinates(countries_gps_coords=selec_countries_gps_coords)
    fuel_sources |= DUMMY_FUEL_SOURCES
    pypsa_model.add_energy_carriers(fuel_sources=fuel_sources)
    pypsa_model.add_generators(generators_data=eraa_dataset.generation_units_data)
    pypsa_model.add_loads(demand=eraa_dataset.demand)
    pypsa_model.add_interco_links(countries=uc_run_params.selected_countries, interco_capas=eraa_dataset.interco_capas)
    with_hydro_custom_const = False  # TODO: set to True/make it a parameter when adding SOC min/max level in model
    with_sum_of_prod_custom_const = len(uc_run_params.sum_prod_constraints) > 0
    if with_hydro_custom_const or with_sum_of_prod_custom_const:
        pypsa_model.build_model_before_adding_custom_const()
    if with_hydro_custom_const:
        # get reservoir extreme generation and level values, as well as energy capacities
        # (to see if constraints will be useless)
        hydro_soc_min, hydro_soc_max, hydro_e_capa = eraa_dataset.get_hydro_params_for_extr_levels_const()
        pypsa_model.add_hydro_extreme_levels_constraint(soc_min=hydro_soc_min, soc_max=hydro_soc_max,
                                                        energy_capa=hydro_e_capa)
    if with_sum_of_prod_custom_const:
        pypsa_model.add_sum_of_prod_custom_const()
    logging.info(f'PyPSA network main properties: {pypsa_model.network}')
    # plot network  
    # name of current "phase" (of the course), the one associated to this script:
    # a multi-zone (Eur.) Unit Commitment model
    phase_name = EnvPhaseNames.multizones_uc_model
    fig_style = (
        read_given_phase_specific_key_from_plot_params(phase_name=phase_name,
                                                       param_to_be_set=PlotParamsKeysInJson.fig_style)
    )
    print_non_default(obj=fig_style, obj_name=f'FigureStyle - for phase {phase_name}', log_level='debug')
    pypsa_model.plot_network(toy_model_output=False)
    return pypsa_model


def solve_pypsa_network_model(pypsa_model: PypsaModel, year: int, n_countries: int, uc_period_start: datetime,
                              solver_params: SolverParams = DEFAULT_OPTIM_SOLVER_PARAMS) \
        -> Tuple[str, str]:
    """
    Solve PyPSA network (UC) model, using an optimisation solver
    :param pypsa_model: to be solved
    :param year: of considered UC pb
    :param n_countries: in the considered network
    :param uc_period_start: date of the beginning of UC pb
    :param solver_params: name/license file, if not default solver (highs) used
    """
    logging.info(f'{TITLE_LOG_SEP} IV) Get a solution for European UC model {TITLE_LOG_SEP}')
    # use alternatively set_optim_solver(name='gurobi', license_file='gurobi.lic') to use Gurobi,
    # with gurobi.lic file provided at root of this project (see readme.md on procedure to obtain such a lic file)
    pypsa_model.set_optim_solver(solver_params=solver_params)
    result = pypsa_model.optimize_network(year=year, n_countries=n_countries, period_start=uc_period_start)
    # Get optim. pb main characteristics (to check if coherent with resolution time?!)
    optim_pb_characts = pypsa_model.get_optim_pb_characteristics()
    logging.info(f'Corresp. to solved {str(optim_pb_characts)}')
    return result


def save_data_and_fig_results(pypsa_model: PypsaModel, uc_run_params: UCRunParams,
                              result_optim_status: str) -> Optional[UCSummaryMetrics]:
    pypsa_opt_resol_status = OPTIM_RESOL_STATUS.optimal
    # if optimal resolution status, save output data and plot associated figures
    if result_optim_status == pypsa_opt_resol_status:
        # get objective value, and associated optimal decisions / dual variables
        objective_value = pypsa_model.get_opt_value(pypsa_resol_status=pypsa_opt_resol_status)
        uc_optimal_solution = pypsa_model.set_uc_opt_solution()
        # get plot parameters associated to aggreg. production types
        per_dim_plot_params = read_plot_params()
        plots_tb_done = (
            read_given_phase_specific_key_from_plot_params(phase_name=EnvPhaseNames.multizones_uc_model,
                                                           param_to_be_set=PlotParamsKeysInJson.plots_tb_done)
        )
        plot_params_agg_pt = per_dim_plot_params[DataDimensions.agg_prod_type]
        plot_params_zone = per_dim_plot_params[DataDimensions.zone]

        # plot - first the ones per country
        for country in uc_run_params.selected_countries:
            # opt. prod profiles 'stacked'
            if PlotNames.prod_stacked in plots_tb_done:
                (uc_optimal_solution.plot_prod(plot_params_agg_pt=plot_params_agg_pt, country=country,
                                               year=uc_run_params.selected_target_year,
                                               climatic_year=uc_run_params.selected_climatic_year,
                                               start_horizon=uc_run_params.uc_period_start)
                 )
            # idem, including stock-like prod units (both cons. and prod.) on the stack of curves
            if PlotNames.prod_stacked_with_stock in plots_tb_done:
                uc_optimal_solution.plot_prod(plot_params_agg_pt=plot_params_agg_pt, country=country,
                                              year=uc_run_params.selected_target_year,
                                              climatic_year=uc_run_params.selected_climatic_year,
                                              start_horizon=uc_run_params.uc_period_start,
                                              include_storage=True)
            # flow in the links
            if PlotNames.link_flows in plots_tb_done:
                (uc_optimal_solution.plot_link_flows(origin_country=country, year=uc_run_params.selected_target_year,
                                                     climatic_year=uc_run_params.selected_climatic_year,
                                                     start_horizon=uc_run_params.uc_period_start)
                 )
        # then plots at the scale of all countries (Europe)
        # 'marginal price' figure
        if PlotNames.marginal_price in plots_tb_done:
            (uc_optimal_solution.plot_marginal_price(plot_params_zone=plot_params_zone,
                                                     year=uc_run_params.selected_target_year,
                                                     climatic_year=uc_run_params.selected_climatic_year,
                                                     start_horizon=uc_run_params.uc_period_start)
             )

        # save optimal prod. decision to an output file
        (uc_optimal_solution.save_decisions_to_csv(year=uc_run_params.selected_target_year,
                                                   climatic_year=uc_run_params.selected_climatic_year,
                                                   start_horizon=uc_run_params.uc_period_start)
         )

        # save marginal prices to an output file
        (uc_optimal_solution.save_marginal_prices_to_csv(year=uc_run_params.selected_target_year,
                                                         climatic_year=uc_run_params.selected_climatic_year,
                                                         start_horizon=uc_run_params.uc_period_start)
         )
        # set UC summary metrics (Energy Not Served, number of failure hours, costs)
        uc_summary_metrics = (
            uc_optimal_solution.set_uc_summary_metrics(network=pypsa_model.network, total_cost=objective_value,
                                                       failure_penalty=uc_run_params.failure_penalty)
        )
        uc_summary_metrics.json_dump(year=uc_run_params.selected_target_year,
                                     climatic_year=uc_run_params.selected_climatic_year,
                                     start_horizon=uc_run_params.uc_period_start)
        return uc_summary_metrics
    else:
        logging.info(f'Optimisation resolution status is not {pypsa_opt_resol_status} '
                     f'-> output data (resp. figures) cannot be saved (resp. plotted), '
                     f'and None UCSummaryMetrics returned')
        per_bus_total_capa = pypsa_model.get_per_bus_total_installed_capa()
        per_bus_max_load = pypsa_model.get_per_bus_max_load()
        infeas_debug_hints_msg = infeas_debugging_hints_msg(total_capa=per_bus_total_capa, max_load=per_bus_max_load)
        logging.info(infeas_debug_hints_msg)
        return None


def run(network_name: str = 'my little europe', solver_params: SolverParams = None,
        fixed_uc_run_params: UCRunParams = None, fixed_run_params_fields: List[str] = None, extra_params: dict = None):
    """
    Run N-zones European Unit Commitment model
    :param network_name: just to set associated attribute in PyPSA network
    :param solver_params: optimisation solver name/license_file; the latter must be at root of this project
    :param fixed_uc_run_params: to impose some values of UCRunParams attributes when running this function;
    it will overwrite the values in input JSON files
    :param fixed_run_params_fields: list of fields to be overwritten
    :param extra_params: dict to gather some additional parameters for dev. usage / debug
        - log_level: it will overwrite the one defined in usage parameters JSON file
        - debug_mode: activated to save some intermediate data/results in (JSON) output files
    to more easily debug the code
    """
    if extra_params is None:
        extra_params = {}

    run_start = time.time()
    output_folder = set_full_lt_uc_output_folder()

    # deactivate some annoying and useless warnings in pypsa/pandas
    deactivate_verbose_warnings()

    # read code environment "usage" parameters
    usage_params = read_usage_params()
    if 'log_level' not in extra_params:
        log_level = usage_params.log_level
    else:
        log_level = extra_params['log_level']

    logger = init_logger(logger_dir=output_folder, logger_name='eraa_lt_uc_pb.log', log_level=log_level)
    logging.info(f'Start ERAA-PyPSA long-term European Unit Commitment (UC) simulation for network: {network_name}')

    logging.info(f'{TITLE_LOG_SEP} I) Read UC run parameters - from European and per-countries JSON input '
                 f'files {TITLE_LOG_SEP}')

    # set fuel sources objects from JSON
    fuel_sources = set_fuel_sources_from_json()

    eraa_data_descr, uc_run_params = (
        read_and_check_uc_run_params(phase_name=EnvPhaseNames.multizones_uc_model, usage_params=usage_params)
    )

    if fixed_uc_run_params is not None:
        uc_run_params = (
            apply_fixed_uc_run_params(uc_run_params=uc_run_params, fixed_uc_run_params=fixed_uc_run_params,
                                      eraa_data_descr=eraa_data_descr, fixed_run_params_fields=fixed_run_params_fields)
        )

    # Get needed data (demand, RES Capa. Factors, installed generation capacities)
    if 'debug_mode' in extra_params:
        debug_mode = extra_params['debug_mode']
    else:
        debug_mode = False
    eraa_dataset = get_needed_eraa_data(uc_run_params=uc_run_params, eraa_data_descr=eraa_data_descr,
                                        debug_mode=debug_mode, debug_output_folder=output_folder)
    # and check that minimal parameters needed for model creation have been provided
    # -> to avoid 'obscure crash' hereafter
    check_min_pypsa_params_provided(eraa_dataset=eraa_dataset)

    # create PyPSA network
    pypsa_model = create_pypsa_network_model(name=network_name, uc_run_params=uc_run_params, eraa_dataset=eraa_dataset,
                                             zones_gps_coords=eraa_data_descr.gps_coordinates,
                                             fuel_sources=fuel_sources)

    # get solver params from JSON file if not provided in arg of this function
    if solver_params is None:
        solver_params = read_solver_params()
    result = solve_pypsa_network_model(pypsa_model=pypsa_model, year=uc_run_params.selected_target_year,
                                       n_countries=len(uc_run_params.selected_countries),
                                       uc_period_start=uc_run_params.uc_period_start, solver_params=solver_params)

    uc_summary_metrics = save_data_and_fig_results(pypsa_model=pypsa_model, uc_run_params=uc_run_params,
                                                   result_optim_status=result[1])

    run_end = time.time()

    logging.info(f'{TITLE_LOG_SEP} THE END of ERAA-PyPSA long-term UC simulation! '
                 f'(after {run_end - run_start:.2f}s) {TITLE_LOG_SEP}:\n{str(uc_summary_metrics)}')
    stop_logger()


if __name__ == '__main__':
    run()
