import json
from typing import List, Dict, Optional, Union
import logging

from common.constants.optimisation import SolverParams
from common.constants.plots import PlotNames
from common.long_term_uc_io import get_json_usage_params_file, get_json_fixed_params_file, \
    get_json_eraa_avail_values_file, get_json_params_tb_modif_file, get_json_pypsa_static_params_file, \
    get_json_params_modif_country_files, get_json_fuel_sources_tb_modif_file, \
    get_json_data_analysis_params_file, get_json_plot_params_file, get_json_solver_params_file, \
    check_uc_input_folder_content
from common.constants.extract_eraa_data import ERAADatasetDescr, \
    PypsaStaticParams, UsageParameters
from common.constants.uc_json_inputs import CountryJsonParamNames, EuropeJsonParamNames, ALL_KEYWORD, \
    EUR_JSON_PARAM_TYPES_FOR_CHECK, EuropeJsonExtraParamNames
from common.constants.usage_params_json import USAGE_PARAMS_SHORT_NAMES, EnvPhaseNames
from common.uc_run_params import UCRunParams
from include.dataset_analyzer import DataAnalysis
from common.plot_params import PlotParams, DEFAULT_PLOT_DIMS_ORDER, PlotParamsKeysInJson, FigureStyle
from utils.basic_utils import get_default_values
from utils.dir_utils import check_file_existence
from utils.type_checker import apply_params_type_check


def check_and_load_json_file(json_file: str, file_descr: str = None) -> dict:
    check_file_existence(file=json_file, file_descr=file_descr)

    f = open(json_file, mode='r', encoding='utf-8')

    # rk: when reading null values in a JSON file they are converted to None
    json_data = json.loads(f.read())

    return json_data


def apply_per_country_json_file_params(countries_data: dict, available_countries: List[str],
                                       mode_name: str, team_name: str) -> dict:
    for file in get_json_params_modif_country_files():
        json_country = check_and_load_json_file(
            json_file=file,
            file_descr='JSON country capacities'
        )
        country = json_country[CountryJsonParamNames.team]
        # TODO[CR]: solo check from global constant/Mode defined in extract_eraa_data.py
        if mode_name == 'solo' and team_name != country:
            continue
        if country not in available_countries:
            logging.error(f'Incorrect country found in file {file}: {country} is not available in dataset')
            exit(1)
        for k, _ in countries_data.items():
            # TODO[CR]: solo check from global constant/Mode defined in extract_eraa_data.py
            if mode_name == 'solo':
                for c, _ in json_country[k].items():
                    logging.info(f'Updating {k} for {c} from file {file}')
                    countries_data[k][c] = json_country[k][c]
            else:
                logging.info(f'Updating {k} for {country} from file {file}')
                countries_data[k][country] = json_country[k][country]
                for c, _ in json_country[k].items():
                    if c != country:
                        logging.warning(f'Ignoring {k} for {country} from file {file}')
    return countries_data


def update_country_json_params(countries_data: dict, json_params_tb_modif: dict) -> (dict, dict):
    """
    Update parameter values obtained from collective file input/long_term_uc/elec-europe_params_to-be-modif.json
    based on the ones of files input/long_term_uc/countries/{country.json}
    """
    selected_pt_param_name = CountryJsonParamNames.selected_prod_types
    if len(countries_data[selected_pt_param_name]) > 0:
        for elt_country, new_prod_types in countries_data[selected_pt_param_name].items():
            logging.info(f'Selected production type(s) overwritten for {elt_country}: {new_prod_types} '
                         f'(and not all the ones from ERAA)')
            json_params_tb_modif[selected_pt_param_name][elt_country] = new_prod_types
    # suppress pt selection key in countries data dict, not to have multiple values for same attr.
    # when creating UCRunParams object hereafter
    del countries_data[selected_pt_param_name]
    return countries_data, json_params_tb_modif


def set_json_usage_params_data() -> dict:
    # read
    json_usage_params_data = check_and_load_json_file(json_file=get_json_usage_params_file(),
                                                      file_descr='JSON usage params')
    # replace long key names by short names (attribute names of following object created)
    json_usage_params_data = {USAGE_PARAMS_SHORT_NAMES[key]: val for key, val in json_usage_params_data.items()}
    return json_usage_params_data


def set_json_eraa_avail_values() -> dict:
    # read
    json_eraa_avail_values = check_and_load_json_file(json_file=get_json_eraa_avail_values_file(),
                                                      file_descr='JSON ERAA available values')
    # add 'available_' to the different keys of JSON available values to make them more explicit in the following
    json_eraa_avail_values = {f'available_{key}': val for key, val in json_eraa_avail_values.items()}
    return json_eraa_avail_values


def set_json_params_fixed() -> dict:
    json_params_fixed = check_and_load_json_file(json_file=get_json_fixed_params_file(), file_descr='JSON fixed params')
    json_eraa_avail_values = set_json_eraa_avail_values()
    # put this dictionary of available values into the 'fixed values' one
    json_params_fixed |= json_eraa_avail_values
    return json_params_fixed


def set_json_solver_params() -> dict:
    return check_and_load_json_file(json_file=get_json_solver_params_file(), file_descr='JSON solver params')


def set_json_params_tb_modif() -> dict:
    return check_and_load_json_file(json_file=get_json_params_tb_modif_file(), file_descr='JSON params to be modif.')


def set_json_fuel_sources_tb_modif() -> dict:
    return check_and_load_json_file(json_file=get_json_fuel_sources_tb_modif_file(),
                                    file_descr='JSON fuel sources params to be modif.')


def set_usage_params(json_usage_params_data: dict) -> UsageParameters:
    usage_params = UsageParameters(**json_usage_params_data)
    usage_params.process()
    return usage_params


def set_eraa_data_descr(json_params_fixed: dict) -> ERAADatasetDescr:
    eraa_data_descr = ERAADatasetDescr(**json_params_fixed)
    eraa_data_descr.check_types()
    eraa_data_descr.process()
    return eraa_data_descr


def set_uc_run_params(json_params_tb_modif: dict, countries_data: dict, json_fuel_sources_tb_modif: dict,
                      eraa_data_descr: ERAADatasetDescr) -> UCRunParams:
    uc_run_params = UCRunParams(**json_params_tb_modif, **countries_data,
                                updated_fuel_sources_params=json_fuel_sources_tb_modif)
    uc_run_params.process(available_countries=eraa_data_descr.available_countries)
    uc_run_params.set_is_stress_test(avail_cy_stress_test=eraa_data_descr.available_climatic_years_stress_test)
    uc_run_params.coherence_check(eraa_data_descr=eraa_data_descr)
    return uc_run_params


def set_countries_data(usage_params: UsageParameters, phase_name: str, available_countries: List[str],
                       json_params_tb_modif: dict) -> (dict, dict):
    selected_pt_param_name = CountryJsonParamNames.selected_prod_types
    countries_data = {
        CountryJsonParamNames.capacities_tb_overwritten: {},
        selected_pt_param_name: {}
    }
    # apply data selection - based on the different JSON files to be modified, and the chosen mode (solo/team)
    apply_per_country_params = usage_params.apply_per_country_json_file_params[phase_name]
    if apply_per_country_params:
        countries_data = (
            apply_per_country_json_file_params(countries_data=countries_data, available_countries=available_countries,
                                               mode_name=usage_params.mode, team_name=usage_params.team)
        )

    # init. selected prod. types, with 'all' value for all selected countries
    json_params_tb_modif[selected_pt_param_name] = \
        {c: [ALL_KEYWORD] for c in json_params_tb_modif[EuropeJsonParamNames.selected_countries]}
    countries_data, json_params_tb_modif = (
        update_country_json_params(countries_data=countries_data, json_params_tb_modif=json_params_tb_modif)
    )

    return countries_data, json_params_tb_modif


def read_usage_params() -> UsageParameters:
    # Get JSON usage params, the ones to control the behaviour of the UC run -> UsageParameters object
    return set_usage_params(json_usage_params_data=set_json_usage_params_data())


def check_and_process_eur_json_tb_modified(json_data: dict):
    json_file = get_json_params_tb_modif_file()
    # first check that keys are coherent
    json_data_keys = list(json_data)
    known_keys = get_default_values(obj=EuropeJsonParamNames)
    unknwon_keys = list(set(json_data_keys) - set(known_keys))
    if len(unknwon_keys) > 0:
        logging.warning(f'Unknown keys in {json_file}: {unknwon_keys} (must be in {known_keys})'
                        f'\n-> will not be taken into account here')
        json_data = {key: val for key, val in json_data.items() if key in known_keys}
    # then that extra-params names are known
    extra_params_key = EuropeJsonParamNames.extra_params
    if extra_params_key in json_data:
        avail_extra_param_names = get_default_values(obj=EuropeJsonExtraParamNames)
        current_extra_param_names = list(json_data[extra_params_key])
        unknown_extra_param_names = list(set(current_extra_param_names) - set(avail_extra_param_names))
        if len(unknown_extra_param_names) > 0:
            logging.warning(f'Unknown extra-param names in {json_file} (keys in dict. associated to '
                            f'{extra_params_key}: {unknown_extra_param_names} (must be in {avail_extra_param_names})'
                            f'\n-> will not be taken into account here')
            json_data[extra_params_key] = \
                {key: val for key, val in json_data[extra_params_key].items() if key in avail_extra_param_names}

    apply_params_type_check(json_data, types_for_check=EUR_JSON_PARAM_TYPES_FOR_CHECK,
                            param_name=f'European params to be modif. (from JSON file {json_file})')
    # suppress first-level extra-params key in json params tb modif dict (if present)
    if extra_params_key in json_data:
        json_data |= json_data[extra_params_key]
        del json_data[extra_params_key]
    return json_data


def read_and_check_uc_run_params(phase_name: str, usage_params: UsageParameters,
                                 get_only_eraa_data_descr: bool = False) \
        -> tuple[ERAADatasetDescr, Optional[UCRunParams]]:
    """
    Read and check parameters for UC run - based on different JSON files (with only part of them that can be modified
    by the users/students in this environment)
    :param phase_name: name of the phase for which this function is run (data analysis, 1-zone UC toy model, X-zones
    Eur. UC model)
    :param usage_params
    :param get_only_eraa_data_descr: used for the runner
    """
    if get_only_eraa_data_descr:
        info_msg = 'Get ERAA data description parameters'
    else:
        json_params_tb_modif_file = get_json_params_tb_modif_file()
        info_msg = f'Read and check long-term UC parameters; the ones modified in file {json_params_tb_modif_file}'
    logging.info(info_msg)

    # get JSON fixed parameters -> ERAA data description object - including in particular the set of
    # available values for countries, (climatic) years, etc.
    eraa_data_descr = set_eraa_data_descr(json_params_fixed=set_json_params_fixed())

    # check that the content of folders containing files to be modified by students is coherent
    check_uc_input_folder_content(all_countries=eraa_data_descr.available_countries)

    # Set countries data, applying data selection/overwriting based on JSON file with values to be modified
    countries_data, json_params_tb_modif = None, None
    if not get_only_eraa_data_descr:
        json_params_tb_modif = set_json_params_tb_modif()
        # check values in JSON params to be modif
        json_params_tb_modif = check_and_process_eur_json_tb_modified(json_data=json_params_tb_modif)
        countries_data, json_params_tb_modif = (
            set_countries_data(usage_params=usage_params, phase_name=phase_name,
                               available_countries=eraa_data_descr.available_countries,
                               json_params_tb_modif=json_params_tb_modif)
        )

    # init. UC run params object
    uc_run_params = None
    if not get_only_eraa_data_descr:
        # fuel sources values modif.
        json_fuel_sources_tb_modif = set_json_fuel_sources_tb_modif()
        uc_run_params = set_uc_run_params(json_params_tb_modif=json_params_tb_modif, countries_data=countries_data,
                                          json_fuel_sources_tb_modif=json_fuel_sources_tb_modif,
                                          eraa_data_descr=eraa_data_descr)

    return eraa_data_descr, uc_run_params


def read_and_check_pypsa_static_params() -> PypsaStaticParams:
    json_pypsa_static_params_file = get_json_pypsa_static_params_file()
    logging.debug(f'Read and check PyPSA static parameters file {json_pypsa_static_params_file}')
    json_pypsa_static_params = check_and_load_json_file(json_file=json_pypsa_static_params_file,
                                                        file_descr='JSON PyPSA static params')
    pypsa_static_params = PypsaStaticParams(**json_pypsa_static_params)
    pypsa_static_params.check_types()
    pypsa_static_params.process()
    return pypsa_static_params


def read_and_check_data_analysis_params(eraa_data_descr: ERAADatasetDescr, n_curves_max: int = 6) -> List[DataAnalysis]:
    """

    Args:
        eraa_data_descr:
        n_curves_max: maximal number of curves on a plot done during DA

    Returns:

    """
    json_data_analysis_params_file = get_json_data_analysis_params_file()
    logging.info(f'Read and check data analysis parameters file; '
                 f'the ones modified in file {json_data_analysis_params_file}')

    json_data_analysis_params = check_and_load_json_file(json_file=json_data_analysis_params_file,
                                                         file_descr='JSON data analysis params')
    data_analysis_params = json_data_analysis_params['data_analysis_list']
    data_analyses = [DataAnalysis(**param_vals) for param_vals in data_analysis_params]
    # check types
    for elt_analysis in data_analyses:
        elt_analysis.check_types()
        elt_analysis.process(eraa_data_descr=eraa_data_descr)
        elt_analysis.coherence_check(eraa_data_descr=eraa_data_descr, n_curves_max=n_curves_max)
    return data_analyses


def read_solver_params() -> SolverParams:
    solver_params_data = set_json_solver_params()
    # a few tests on read JSON file
    name_key = 'name'
    lic_file_key = 'license_file'
    known_keys = [name_key, lic_file_key]
    solver_params_file = get_json_solver_params_file()
    if name_key not in solver_params_data:
        raise Exception(f'Mandatory param {name_key} missing in {solver_params_file} -> STOP')
    if lic_file_key not in solver_params_data:
        logging.info(f'Param {lic_file_key} missing in {solver_params_file} -> default optim. solver will be used')
    unknown_params = list(set(solver_params_data) - set(known_keys))
    if len(unknown_params) > 0:
        logging.warning(f'There are unknown parameters in {solver_params_file}: {unknown_params} -> will not be used')
    solver_params_data = {key: solver_params_data[key] for key in known_keys}
    return SolverParams(**solver_params_data)


def read_given_phase_specific_key_from_plot_params(phase_name: str, param_to_be_set: str) -> Union[
    FigureStyle, List[str]]:
    """
    Read given phase specific parameters from plot_params.json file
    Args:
        phase_name: 'data_analysis', 'monozone_toy_uc_model', or 'multizones_uc_model'
        param_to_be_set: either figure style, or list of plots to be done
    Returns: either a FigureStyle object or a list of plot names; according to param_to_be_set value
    """
    allowed_params_tb_set = [PlotParamsKeysInJson.fig_style, PlotParamsKeysInJson.plots_tb_done]
    json_plot_params_file = get_json_plot_params_file()
    if param_to_be_set not in allowed_params_tb_set:
        raise Exception(f'Param to be set {param_to_be_set} when reading {json_plot_params_file} for '
                        f'phase {phase_name} must be in {allowed_params_tb_set}')
    logging.debug(f'Read and check {phase_name} plot parameters file: {json_plot_params_file}'
                  f'\n-> to set {param_to_be_set}')
    json_data_analysis_plot_params = check_and_load_json_file(json_file=json_plot_params_file,
                                                              file_descr=f'JSON {phase_name} plot params')
    key_in_json = f'{param_to_be_set}_{phase_name}'
    if param_to_be_set == PlotParamsKeysInJson.fig_style:
        return FigureStyle(**json_data_analysis_plot_params[key_in_json])
    else:
        plots_tb_done = json_data_analysis_plot_params[key_in_json]
        # default value for plots to be done -> all plot names
        all_plots_tb_done = get_default_values(obj=PlotNames)
        if plots_tb_done is None:
            plots_tb_done = all_plots_tb_done
        else:  # check that set values are known
            # that all figs to be done are known
            unknown_plot_names = set(plots_tb_done) - set(all_plots_tb_done)
            if len(unknown_plot_names) > 0:
                logging.warning(f'Unknown plots to be done in {json_plot_params_file} file {unknown_plot_names} '
                                f'for key {key_in_json}\n-> will not be used in plotting phase')
                plots_tb_done = [name for name in plots_tb_done if name in all_plots_tb_done]
        return plots_tb_done


def read_plot_params() -> Dict[str, PlotParams]:
    """
    Read plot parameters
    Returns: list of plots to be done, per dimension (aggreg. prod types, zones, ...) plot params
    """
    json_plot_params_file = get_json_plot_params_file()
    logging.debug(f'Read and check plot parameters file: {json_plot_params_file}')

    json_plot_params = check_and_load_json_file(json_file=json_plot_params_file, file_descr='JSON plot params')
    # remove elt used only for FigureStyle of data analysis / idem for list of plots to be done
    for phase_name in [EnvPhaseNames.data_analysis, EnvPhaseNames.monozone_toy_uc_model,
                       EnvPhaseNames.multizones_uc_model]:
        for param_name in [PlotParamsKeysInJson.fig_style, PlotParamsKeysInJson.plots_tb_done]:
            current_key = f'{param_name}_{phase_name}'
            if current_key in json_plot_params:
                del json_plot_params[current_key]

    per_dim_plot_params = {}
    for plot_dim in DEFAULT_PLOT_DIMS_ORDER:
        dict_params = json_plot_params[plot_dim]
        dict_params['dimension'] = plot_dim
        current_plot_params = PlotParams(**dict_params)
        current_plot_params.process()
        current_plot_params.check(json_plot_params_file=json_plot_params_file)
        per_dim_plot_params[plot_dim] = current_plot_params

    return per_dim_plot_params
