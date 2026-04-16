# -*- coding: utf-8 -*-
"""
First very simple toy Unit Commitment (UC) model of Italy zone - alone -> with PyPSA and ERAA data
-> you can copy/paste some piece of this code to obtain your my_toy_ex_{country}.py own script
"""
from common.error_msgs import infeas_debugging_hints_msg

"""
  0) Preliminar functional aspects / technical functions
  -> not useful to look at/analyse them
  -> just copy/paste them in your own script
"""
# (0.a) deactivate some verbose warnings (mainly in pandas, pypsa)
from common.logger import deactivate_verbose_warnings

deactivate_verbose_warnings(deact_deprecation_warn=True)

# (0.b) Function to get an object describing ERAA dataset (mainly available values)
from common.constants.extract_eraa_data import ERAADatasetDescr


def get_eraa_data_description() -> ERAADatasetDescr:
    from common.long_term_uc_io import get_json_fixed_params_file
    json_fixed_params_file = get_json_fixed_params_file()
    from utils.read import check_and_load_json_file
    json_params_fixed = check_and_load_json_file(json_file=json_fixed_params_file,
                                                 file_descr='JSON fixed params')
    json_available_values_dummy = {'available_climatic_years': None,
                                   'available_countries': None,
                                   'available_aggreg_prod_types': None,
                                   'available_intercos': None,
                                   'available_target_years': None}
    json_params_fixed |= json_available_values_dummy

    return ERAADatasetDescr(**json_params_fixed)


# Function to get a few parameters for plot -> only style, in particular to set fixed colors
# per (aggreg.) production type/country
from common.plot_params import PlotParams, PlotParamsKeysInJson


def get_plots_params() -> (PlotParams, PlotParams):
    from utils.read import read_plot_params
    per_dim_plot_params = read_plot_params()
    from utils.read import read_given_phase_specific_key_from_plot_params
    fig_style = (
        read_given_phase_specific_key_from_plot_params(phase_name=phase_name, param_to_be_set=PlotParamsKeysInJson.fig_style)
    )
    from utils.basic_utils import print_non_default
    print_non_default(obj=fig_style, obj_name=f'FigureStyle - for phase {phase_name}', log_level='debug')
    return per_dim_plot_params[DataDimensions.agg_prod_type], per_dim_plot_params[DataDimensions.zone]


# name of current "phase" (of the course), the one associated to this script: a 1-zone Unit Commitment model
from common.constants.usage_params_json import EnvPhaseNames

phase_name = EnvPhaseNames.monozone_toy_uc_model

"""
  I) Set global parameters for the case simulated -> choosing
    (1) country
    (2) (future) year
    (3) climatic year
    (4) period (in the year) to be considered for the simulated UC 
"""
# (I.1) unique country modeled in this example -> some comments are provided below to explain how PyPSA model could be
# extended to a multiple countries case (if you have time - and motivation! - to test it on your own)
# See [N-countries] tags
country = 'italy'
# (I.2) select first ERAA year available, as an example (2033 also available)
# -> available values [2025, 2033]
year = 2025
# (I.3) and a given "climatic year" (to possibly test different climatic*weather conditions)
# -> available values [1982, 1989, 1996, 2003, 2010, 2016]
# N.B. Ask Boutheina OUESLATI (R&D of EDF) on Thursday to get an idea of the 'climatic' versus 'weather' conditions
climatic_year = 1989
# (I.4) Set start and end date corresponding to the period to be simulated
# ATTENTION: uc_period_end not included -> here period {1900/1/1 00:00, 1900/1/1 01:00, ..., 1900/1/13 23:00}
# N.B. Calendar of year 1900 used here, to make explicit the fact that ERAA data are 'projected'
# on a fictive calendar - made of 52 full weeks
from datetime import datetime, timedelta

uc_period_start = datetime(year=1900, month=1, day=1)
uc_period_end = uc_period_start + timedelta(days=14)
from common.constants.prod_types import ProdTypeNames

agg_prod_types_selec = [ProdTypeNames.wind_onshore, ProdTypeNames.wind_offshore, ProdTypeNames.solar_pv]

"""
  II) Initialize two objects - used hereafter to have clean and 'robust' code operations/functions
  -> operations that you can directly copy/paste in your own script; except if you would like to directly re-code on 
  your side using the PyPSA framework (ask us some help if needed!)
    (1) UCRunParams
    (2) (ERAA) Dataset
"""
# (II.a) UC main run parameters (dictionary gathering main characteristics of the pb simulated)
from common.uc_run_params import UCRunParams

selected_countries = [country]  # [N-countries] Add other country names
uc_run_params = UCRunParams(selected_countries=selected_countries, selected_target_year=year,
                            selected_climatic_year=climatic_year,
                            selected_prod_types={country: agg_prod_types_selec},
                            uc_period_start=uc_period_start,
                            uc_period_end=uc_period_end)

# (II.b) Dataset object
from include.dataset import Dataset

eraa_data_descr = get_eraa_data_description()
eraa_dataset = Dataset(agg_prod_types_with_cf_data=eraa_data_descr.agg_prod_types_with_cf_data)

"""
  III) Get needed data - from ERAA csv files in data\ERAA_2023-2
    (1) "Extract" data from csv files provided in this project
    (2) An example on how to access to the obtained data for some "production types"
"""

# (III.1) Get data for Italy... just for test -> data used when writing PyPSA model will be re-obtained afterwards
eraa_dataset.get_countries_data(uc_run_params=uc_run_params,
                                aggreg_prod_types_def=eraa_data_descr.aggreg_prod_types_def)
eraa_dataset.complete_data()

# (III.2) Accessing the data: globally all is made with pandas dataframes (df)
# In this case, for ex. decompose aggregated Capacity Factor data into three sub-dictionaries
# (for following code to be more explicit)
from utils.df_utils import selec_in_df_based_on_list
# use global constant names of different production types to be sure of extracting data without any pb
from common.constants.prod_types import ProdTypeNames

prod_type_col = 'production_type_agg'
solar_pv_cf_data = {
    country: selec_in_df_based_on_list(df=eraa_dataset.agg_cf_data[country], selec_col=prod_type_col,
                                       selec_vals=[ProdTypeNames.solar_pv], rm_selec_col=True)
}
wind_onshore_cf_data = {
    country: selec_in_df_based_on_list(df=eraa_dataset.agg_cf_data[country], selec_col=prod_type_col,
                                       selec_vals=[ProdTypeNames.wind_onshore], rm_selec_col=True)
}
wind_offshore_cf_data = {
    country: selec_in_df_based_on_list(df=eraa_dataset.agg_cf_data[country], selec_col=prod_type_col,
                                       selec_vals=[ProdTypeNames.wind_offshore], rm_selec_col=True)
}
# N.B. Both reservoir and open-loop pump-storage inflow values are in the same df - a bit different operation 
# compared to data getter for RES CF data
hydro_reservoir_inflows_data = {
    country: eraa_dataset.hydro_inflows_data[country][['date', 'cum_inflow_into_reservoirs']]}
open_loop_pump_sto_inflows_data = {
    country: eraa_dataset.hydro_inflows_data[country][['date', 'cum_nat_inflow_into_pump-storage_reservoirs']]}
# rename columns to get 'value' column name for all data after this stage
from utils.df_utils import rename_df_columns

value_col = 'value'
hydro_reservoir_inflows_data = \
    {c: rename_df_columns(df=df, old_to_new_cols={'cum_inflow_into_reservoirs': value_col})
     for c, df in hydro_reservoir_inflows_data.items()}
open_loop_pump_sto_inflows_data = \
    {c: rename_df_columns(df=df, old_to_new_cols={'cum_nat_inflow_into_pump-storage_reservoirs': value_col})
     for c, df in open_loop_pump_sto_inflows_data.items()}

"""
  IV) Build PyPSA model - with unique country (Italy here)
    (1) Initialize a network, the key component in PyPSA
    (2) Define specific parameters of your country to this network model 
    KEY POINT: main parameters needed for Italy description in PyPSA are set in script 
    toy_model_params/italy_parameters.py
    To get the meaning and format of main PyPSA objects/attributes look at file doc/toy-model_tutorial.md
    In your case you will have to reproduce such a file for your own country
    Step-by-step:
      (i) Add bus
      (ii) Add generators
      (iii) Add demand
      (iv) Check/observe that created network be coherent
"""
# (IV.1) Initialize PyPSA Network (basis of all your simulations this week!)
# -> "encapsulated" in a PypsaModel used in this code project
print('Initialize PyPSA network')
# For brevity, set country trigram as the 'id' of your country in following model definition (and observed outputs)
from include.dataset_builder import set_country_trigram

country_trigram = set_country_trigram(country=country)
from include.dataset_builder import PypsaModel

pypsa_model = PypsaModel(name=f'my 1-zone {country_trigram} toy model')
# set a date horizon, to have more explicit axis labels hereafter
# -> will be used as "snapshots" in PyPSA
# -> for ex. as a list of indices (other formats; like data ranges can be used instead)
import pandas as pd

date_idx = eraa_dataset.demand[uc_run_params.selected_countries[0]].index
horizon = pd.date_range(
    start=uc_run_params.uc_period_start.replace(year=uc_run_params.selected_target_year),
    end=uc_run_params.uc_period_end.replace(year=uc_run_params.selected_target_year),
    freq='h'
)
pypsa_model.init_pypsa_network(date_idx=date_idx, date_range=horizon)
# And print it to check that for now it is... empty
print(pypsa_model.network)

# (IV.2) Define Italy parameters
# (IV.2.i) Add bus for considered country
# N.B. Italy coordinates set randomly! (not useful in the calculation that will be done this week)
# [N-countries] Add key, values (tuple of coordinates) to the following 'coordinates' dictionary
from toy_model_params.italy_parameters import gps_coords

coordinates = {country: gps_coords}
pypsa_model.add_gps_coordinates(countries_gps_coords=coordinates)

# (IV.2.ii) [VERY KEY - AND TRICKY :) - STAGE] Generators definition, beginning with only simple parameters.
# Almost 'real Italy'... excepting hydraulic storage and Demand-Side Response capacity 
# (we will come back on this later)
# Thanks to Tim WALTER - student of a past similar course, detailed parameter values associated
# to different fuel sources are available in following dictionary. You can use it or search/define 
# fictive alternative values instead -> plenty infos on Internet on this... sometimes of 'varying' quality! 
# (keeping format of dataclass - sort of enriched dictionary -, just change values directly in
# file toy_model_params/{country}_parameters.py)
from common.fuel_sources import set_fuel_sources_from_json, DUMMY_FUEL_SOURCES
from toy_model_params.italy_parameters import get_generators, set_gen_as_list_of_gen_units_data

fuel_sources = set_fuel_sources_from_json()

# get properties of generators to be set on the unique considered bus here
# -> from toy_model_params/italy_parameters.py script
generators = get_generators(country_trigram=country_trigram, fuel_sources=fuel_sources,
                            wind_onshore_cf_data=wind_onshore_cf_data[country],
                            wind_offshore_cf_data=wind_offshore_cf_data[country],
                            solar_pv_cf_data=solar_pv_cf_data[country],
                            hydro_reservoir_inflows_data=hydro_reservoir_inflows_data[country],
                            open_loop_pump_sto_inflows_data=open_loop_pump_sto_inflows_data[country])
# set generation units data from this list
generation_units_data = set_gen_as_list_of_gen_units_data(generators=generators)
# [N-countries] Add country (key), generation units data (values) to the gen_units_data argument
# of function below
eraa_dataset.set_generation_units_data(gen_units_data={country: generation_units_data})

# add "dummy" fuel sources (not primary energies); to avoid multiple "undefined energy carriers" warnings in PyPSA
fuel_sources |= DUMMY_FUEL_SOURCES
# add generators to the PyPSA network
# -> have a look to the following methods if you want to see how it is coded in PyPSA framework
pypsa_model.add_energy_carriers(fuel_sources=fuel_sources)
pypsa_model.add_per_bus_energy_carriers(fuel_sources=fuel_sources)
pypsa_model.add_generators(generators_data=eraa_dataset.generation_units_data)

# IV.2.iii) Add load
# [N-countries] Add country name (key), demand (values) in eraa_dataset.demand used below
pypsa_model.add_loads(demand=eraa_dataset.demand)

# IV.2.iv) Check/observe that created PyPSA model be coherent
print(f'PyPSA network main properties: {pypsa_model.network}')
# Plot it. Surely better when having multiple buses (countries)!!
# N.B. Setting toy_model_output to True is just to have the plotted figure saved in a subfolder monozone_ita
pypsa_model.plot_network(toy_model_output=True, country=country)
# Print out list of generators
print(pypsa_model.network.generators)

"""
  V) 'Optimize network' i.e., solve the associated (1-zone) Unit-Commitment problem
    (1) Set solver to be used
    (2) Save .lp file to check/observe the equations of the optim. pb that will be solved, and solve it
"""
# (V.1) Set solver to be used
# -> default is to use "highs", that must be largely sufficient to solve this 1-zone UC toy model
# -> alternatively pypsa_model.set_optim_solver(name='gurobi', license_file='gurobi.lic') can be used,
# with gurobi.lic file provided at root of this project (see readme.md for procedure to obtain such a .lic file)
pypsa_model.set_optim_solver()
# (V.2) Save lp model, then solve optimisation model (using either highs/gurobi)
# N.B. .lp files is a standard format containing the equations associated to the solved optim. problem
# -> will be saved in output folder output/long_term_uc/monozone_{country trigram}/data
# you can observe if you find the equations corresponding to the UC problem modeled
result = pypsa_model.optimize_network(year=uc_run_params.selected_target_year, n_countries=1,
                                      period_start=uc_run_params.uc_period_start, save_lp_file=True,
                                      toy_model_output=True, countries=[country])
print(f'PyPSA result: {result}')  # Check 2nd component of result, the resolution status (optimal?)
# Get optim. pb main characteristics (to check if coherent with resolution time?!)
optim_pb_characts = pypsa_model.get_optim_pb_characteristics()
print(f'Corresp. to solved {str(optim_pb_characts)}')

"""
  VI) Analyse/plot obtained UC solution (production of the different units?)
    (1) Get and check optimisation status. VERY KEY to be sure that a solution has been found to the UC model
    (2) Save data/plot to analyse in detail the obtained solution 
"""
# (V1.1) Get objective value, and associated optimal decisions / dual variables
from common.constants.optimisation import OPTIM_RESOL_STATUS

optim_status = result[1]
pypsa_opt_resol_status = OPTIM_RESOL_STATUS.optimal
# (V1.2) If optimal resolution status, save output data and plot associated figures
if optim_status == pypsa_opt_resol_status:
    objective_value = pypsa_model.get_opt_value(pypsa_resol_status=pypsa_opt_resol_status)
    from utils.basic_utils import format_with_spaces
    print(f'Total cost at optimum: {format_with_spaces(number=int(objective_value/1e6))} M€')
    # Look at the following method - decomposed per variable - if you want to see how to access optimal decisions
    # in PyPSA framework
    uc_optimal_solution = pypsa_model.set_uc_opt_solution()

    print('Plot installed capacities (INPUT parameter), generation and prices (optimisation OUTPUTS) figures')
    # Plot installed capacities
    pypsa_model.plot_installed_capas(country=country, year=uc_run_params.selected_target_year, toy_model_output=True)
    # Plot 'stack' of optimised production profiles -> key graph to interpret UC solution -> will be
    # saved in file output/long_term_uc/monozone_ita/figures/prod_italy_{year}_{period start, under format %Y-%m-%d}.png
    # get plot parameters associated to aggreg. production types
    from common.constants.datadims import DataDimensions

    plot_params_agg_pt, plot_params_zone = get_plots_params()
    # graph with stack production
    uc_optimal_solution.plot_prod(plot_params_agg_pt=plot_params_agg_pt, country=country,
                                  year=uc_run_params.selected_target_year,
                                  climatic_year=uc_run_params.selected_climatic_year,
                                  start_horizon=uc_run_params.uc_period_start,
                                  toy_model_output=True)
    # idem, including stock-like prod units (both cons. and prod.) on the stack of curves
    uc_optimal_solution.plot_prod(plot_params_agg_pt=plot_params_agg_pt, country=country,
                                  year=uc_run_params.selected_target_year,
                                  climatic_year=uc_run_params.selected_climatic_year,
                                  start_horizon=uc_run_params.uc_period_start,
                                  toy_model_output=True, include_storage=True)
    # Specific production profile: the one of fictive failure asset
    uc_optimal_solution.plot_failure(country=country, year=uc_run_params.selected_target_year,
                                     climatic_year=uc_run_params.selected_climatic_year,
                                     start_horizon=uc_run_params.uc_period_start,
                                     toy_model_output=True)
    # Finally, plot 'marginal prices' -> QUESTION: meaning?
    # -> saved in file output/long_term_uc/monozone_ita/figures/prices_italy_{year}
    # _{period start, under format %Y-%m-%d}.png
    # QUESTION: how can you interpret the very constant value plotted?
    uc_optimal_solution.plot_marginal_price(plot_params_zone=plot_params_zone, year=uc_run_params.selected_target_year,
                                            climatic_year=uc_run_params.selected_climatic_year,
                                            start_horizon=uc_run_params.uc_period_start, toy_model_output=True,
                                            country=country)

    # Save optimal decisions to output csv files -> you can have look in more detail to the obtained solution
    print('Save optimal dispatch decisions to .csv file')
    # (Per unit type) Production decisions
    uc_optimal_solution.save_decisions_to_csv(year=uc_run_params.selected_target_year,
                                              climatic_year=uc_run_params.selected_climatic_year,
                                              start_horizon=uc_run_params.uc_period_start, toy_model_output=True,
                                              country=country)

    # Marginal prices
    uc_optimal_solution.save_marginal_prices_to_csv(year=uc_run_params.selected_target_year,
                                                    climatic_year=uc_run_params.selected_climatic_year,
                                                    start_horizon=uc_run_params.uc_period_start, toy_model_output=True,
                                                    country=country)
else:
    print(f'Optimisation resolution status is not {pypsa_opt_resol_status} '
          f'-> output data (resp. figures) cannot be saved (resp. plotted), excepting installed capas one')
    total_capa = sum(g['p_nom'] for g in generators if 'p_nom' in g)
    max_load = eraa_dataset.demand[country].max().values[0]
    infeas_debug_hints_msg = infeas_debugging_hints_msg(total_capa=total_capa, max_load=max_load)
    print(infeas_debug_hints_msg)
    pypsa_model.plot_installed_capas(country=country, year=uc_run_params.selected_target_year,
                                     toy_model_output=True)

print(f'THE END of ERAA-PyPSA long-term UC toy model of country {country} simulation!')
