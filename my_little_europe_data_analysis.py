from itertools import product

import logging

from common.constants.datatypes import DATATYPE_NAMES
from common.constants.usage_params_json import EnvPhaseNames
from common.logger import init_logger, stop_logger
from common.long_term_uc_io import OUTPUT_DATA_ANALYSIS_FOLDER
from common.plot_params import PlotParamsKeysInJson
from include.dataset import Dataset
from utils.basic_utils import print_non_default
from utils.dates import get_period_str
from utils.read import read_and_check_data_analysis_params, read_and_check_uc_run_params, \
    read_given_phase_specific_key_from_plot_params, read_plot_params, read_usage_params

phase_name = EnvPhaseNames.data_analysis

# read code environment "usage" parameters
usage_params = read_usage_params()
logger = init_logger(logger_dir=OUTPUT_DATA_ANALYSIS_FOLDER, logger_name='eraa_input_data_analysis.log',
                     log_level=usage_params.log_level)
logging.info('START ERAA (input) data analysis')

# read ERAA data description (JSON) file, and UC run parameters
eraa_data_descr, uc_run_params = read_and_check_uc_run_params(phase_name=phase_name, usage_params=usage_params)

# set params and figure style for plots
per_dim_plot_params = read_plot_params()
fig_style = read_given_phase_specific_key_from_plot_params(phase_name=phase_name,
                                                           param_to_be_set=PlotParamsKeysInJson.fig_style)
print_non_default(obj=fig_style, obj_name=f'FigureStyle - for phase {phase_name}', log_level='debug')

# read and check data analyses params
data_analyses = read_and_check_data_analysis_params(eraa_data_descr=eraa_data_descr,
                                                    n_curves_max=fig_style.n_curves_max)

# loop over the different cases to be analysed
for elt_analysis in data_analyses:
    logging.info(elt_analysis)
    # set UC run params to the ones corresponding to this analysis
    current_countries = elt_analysis.countries
    uc_run_params.set_countries(countries=current_countries)
    uc_run_params.set_uc_period(start=elt_analysis.period_start, end=elt_analysis.period_end)
    uc_period_msg = get_period_str(period_start=uc_run_params.uc_period_start, period_end=uc_run_params.uc_period_end)
    # currently loop over year, climatic_year; given that UC run params made for a unique (year, climatic year) couple
    # init. dict. to save data for each (country, year, clim_year) tuple
    current_df = {}
    dt_suffix_for_output = None  # suffix to be added to datatype in output files to identify them in specific cases
    for year, clim_year, current_extra_params in (
            product(elt_analysis.years, elt_analysis.climatic_years, elt_analysis.extra_params)):
        uc_run_params.set_target_year(year=year)
        uc_run_params.set_climatic_year(climatic_year=clim_year)
        # Attention check at each time if stress test based on the set year
        uc_run_params.set_is_stress_test(avail_cy_stress_test=eraa_data_descr.available_climatic_years_stress_test)
        # And if coherent climatic year, i.e. in list of available data
        uc_run_params.coherence_check_ty_and_cy(eraa_data_descr=eraa_data_descr, stop_if_error=True)

        logging.info(f'Read needed ERAA ({eraa_data_descr.eraa_edition}) data for period {uc_period_msg}')
        # initialize dataset object
        eraa_dataset = Dataset(source=f'eraa_{eraa_data_descr.eraa_edition}',
                               agg_prod_types_with_cf_data=eraa_data_descr.agg_prod_types_with_cf_data,
                               is_stress_test=uc_run_params.is_stress_test)

        if current_extra_params is None:
            extra_params_vals = {}
            extra_params_idx = None
        else:
            extra_params_vals = current_extra_params.values
            extra_params_idx = current_extra_params.index
        # get data to be analyzed/plotted hereafter - using extra-parameters if provided
        # TODO: cleaner...
        subdt_selec = elt_analysis.aggreg_prod_types if not elt_analysis.aggreg_prod_types == [None] else None
        eraa_dataset.get_countries_data(uc_run_params=uc_run_params,
                                        aggreg_prod_types_def=eraa_data_descr.aggreg_prod_types_def,
                                        datatypes_selec=[elt_analysis.data_type],
                                        subdt_selec=subdt_selec, **extra_params_vals)
        eraa_dataset.complete_data()
        per_dt_data = {DATATYPE_NAMES.demand: eraa_dataset.demand,
                       DATATYPE_NAMES.capa_factor: eraa_dataset.agg_cf_data,
                       DATATYPE_NAMES.net_demand: eraa_dataset.net_demand,
                       DATATYPE_NAMES.fatal_production: eraa_dataset.fatal_prod}
        # create Unit Commitment Timeseries object from data read
        if elt_analysis.data_type in per_dt_data:
            # loop over country to extract per-country data from dataset.
            # N.B. year and climatic_year have been uniquely set up when init. the Dataset object
            for country in current_countries:
                current_df[(country, year, clim_year, extra_params_idx)] = per_dt_data[elt_analysis.data_type][country]
        else:
            for country in current_countries:
                current_df[(country, year, clim_year, extra_params_idx)] = None
    # get potential dt suffix to be added to figure filename (to identify it)
    dt_suffix_for_output = elt_analysis.get_dt_suffix_for_output()

    extra_params_labels = elt_analysis.get_extra_args_idx_to_label_corresp()
    elt_analysis.apply_analysis(per_case_data=current_df, fig_style=fig_style, per_dim_plot_params=per_dim_plot_params,
                                extra_params_labels=extra_params_labels, dt_suffix_for_output=dt_suffix_for_output)

logging.info('THE END of ERAA (input) data analysis!')
stop_logger()
