import logging
from typing import List

from common.constants.extract_eraa_data import ERAADatasetDescr
from common.uc_run_params import UCRunParams, overwrite_uc_run_params
from utils.basic_utils import get_all_attr_names


def apply_fixed_uc_run_params(uc_run_params: UCRunParams, fixed_uc_run_params: UCRunParams,
                              eraa_data_descr: ERAADatasetDescr,
                              fixed_run_params_fields: List[str] = None) -> UCRunParams:
    """
    Overwrite (some of the attrs) of a UCRunParams object based on another object of this class
    """
    if fixed_run_params_fields is None:
        fixed_run_params_fields = get_all_attr_names(obj=UCRunParams)
    logging.info(f'Apply UCRunParams imposed values in Python args (of script my_little_europe_lt_uc.py) '
                 f'for fields: {fixed_run_params_fields}')
    logging.info(f'UCRunParams BEFORE overwriting: {str(uc_run_params)}')
    # overwrite some attr. values of UCRunParams by the ones provided in arg. of this function
    # first process and check coherence of imposed values. N.B. Do not fullfill prod types values
    # for non-selected countries in this case
    fixed_uc_run_params.process(available_countries=eraa_data_descr.available_countries, fullfill_selected_pt=False)
    fixed_uc_run_params.coherence_check(eraa_data_descr=eraa_data_descr)
    uc_run_params = overwrite_uc_run_params(uc_run_params=uc_run_params, uc_run_params_2=fixed_uc_run_params,
                                            fields_tb_overwritten=fixed_run_params_fields)
    # check coherence again, as mixing attrs of two UCRunParams objects can introduce issues (e.g., if stress test
    # is used with a climatic year in the set of standard ones)
    uc_run_params.coherence_check(eraa_data_descr=eraa_data_descr)
    logging.info(f'UCRunParams AFTER overwriting: {str(uc_run_params)}')
    return uc_run_params
