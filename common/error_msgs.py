import sys
import logging
from typing import List, Dict, Union


def print_errors_list(error_name: str, errors_list: List[str]):
    error_msg = f'There are error(s) {error_name}:'
    for elt_error in errors_list:
        error_msg += f'\n- {elt_error}'
    error_msg += '\n-> STOP'
    logging.error(error_msg)
    sys.exit(1)
    

def uncoherent_param_stop(param_errors: List[str]):
    print_errors_list(error_name='in JSON params to be modif. file', errors_list=param_errors)


def unknown_value_error(var_name: str, value, available_values: list = None) -> str:
    error_msg = f'Unknown {var_name} {value}'
    if available_values is not None:
        error_msg += f'it must be in {available_values}'
    return error_msg


def infeas_debugging_hints_msg(total_capa: Union[float, Dict[str, float]],
                               max_load: Union[float, Dict[str, float]]) -> str:
    """
    Set a debugging hint message in case of infeasibility observed in UC optimisation (to guide students on how to
    fix it)
    Args:
        total_capa: can be either a number (in a 1-bus/zone model) or a dict {bus name: corresp. capa}
        max_load: idem

    Returns: message to be printed out

    """
    info_msg = "Debugging hints:"
    info_msg += "\n  1. Does the total installed capacity cover the peak demand?"
    if isinstance(total_capa, dict):
        per_bus_msg = '(Per bus) '
    info_msg += f"\n     {per_bus_msg}Maximum observed demand: {max_load:.0f} MW"
    info_msg += f"     {per_bus_msg}Total installed capacity: {total_capa:.0f} MW"
    info_msg += "  2. Is failure_power_capa large enough?"
    info_msg += "  3. Are storage constraints (hydro, batteries) consistent?"
    info_msg += "  4. Does the simulated period actually contain ERAA data?"
    return info_msg
