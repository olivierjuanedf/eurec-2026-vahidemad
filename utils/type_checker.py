from typing import Dict
from dataclasses import dataclass

from common.error_msgs import print_errors_list


@dataclass
class CheckerNames:
    is_dict: str = 'dict'
    is_str: str = 'str'
    is_int: str = 'int'
    is_float: str = 'float'
    is_list_of_int: str = 'list_of_int'
    is_list_of_str: str = 'list_of_str'
    is_none_or_list_of_str: str = 'none_or_list_of_str'
    is_dict_str_dict: str = 'dict_str_dict'
    is_dict_str_list_of_float: str = 'dict_str_list_of_float'  # {str: List[float]}
    is_dict_str_list_of_str: str = 'dict_str_list_of_str'  # {str: List[str]}
    is_dict_str_int: str = 'dict_str_int'  # {str: int}
    is_dict_str_str: str = 'dict_str_str'  # {str: str}
    is_two_level_dict_str_str_list_of_str: str = 'two_level_dict_str_str_list-of-str'
    is_two_level_dict_str_str_str: str = 'two_level_dict_str_str_str'
    # "combination" of checkers above
    is_str_or_list_of_str: str = 'str_or_list_of_str'
    is_int_or_list_of_int: str = 'int_or_list_of_int'


def check_dict(data_val) -> bool:
    return isinstance(data_val, dict)


# basic checker
def check_str(data_val) -> bool:
    return isinstance(data_val, str)


def check_int(data_val) -> bool:
    return isinstance(data_val, int)


def check_float(data_val) -> bool:
    return isinstance(data_val, float)


# lists of a given type
def check_list_of_given_type(data_val, needed_type: type) -> bool:
    if not isinstance(data_val, list):
        return False
    return all([isinstance(elt, needed_type) for elt in data_val])


def check_list_of_str(data_val) -> bool:
    return check_list_of_given_type(data_val=data_val, needed_type=str)


def check_list_of_int(data_val) -> bool:
    return check_list_of_given_type(data_val=data_val, needed_type=int)


def check_list_of_float(data_val) -> bool:
    return check_list_of_given_type(data_val=data_val, needed_type=float)


def check_none_or_list_of_str(data_val) -> bool:
    if data_val is None:
        return True
    return check_list_of_str(data_val=data_val)


# complex dicts
def check_str_str_dict(data_val) -> bool:
    if not isinstance(data_val, dict):
        return False
    keys_and_vals = list(data_val.keys())
    keys_and_vals.extend(data_val.values())
    return all([isinstance(elt, str) for elt in keys_and_vals])


def check_str_int_dict(data_val) -> bool:
    if not isinstance(data_val, dict):
        return False
    keys = list(data_val.keys())
    vals = list(data_val.values())
    return check_list_of_str(data_val=keys) and check_list_of_int(data_val=vals)


def check_str_list_of_str_dict(data_val) -> bool:
    if not isinstance(data_val, dict):
        return False
    keys = list(data_val.keys())
    vals = list(data_val.values())
    return check_list_of_str(data_val=keys) and \
        all([check_list_of_str(data_val=val) for val in vals])


def check_str_list_of_float_dict(data_val) -> bool:
    if not isinstance(data_val, dict):
        return False
    keys = list(data_val.keys())
    vals = list(data_val.values())
    return check_list_of_str(data_val=keys) and \
        all([check_list_of_float(data_val=val) for val in vals])


def check_str_dict_dict(data_val) -> bool:
    """
    Check that data_val be of type {str: dict}
    """
    if not isinstance(data_val, dict):
        return False
    keys = list(data_val.keys())
    vals = list(data_val.values())
    return check_list_of_str(data_val=keys) and all([isinstance(val, dict) for val in vals])


def check_three_level_str_dict(data_val) -> bool:
    if not isinstance(data_val, dict):
        return False
    return all([(isinstance(key, str) and check_str_str_dict(data_val=val)) for key, val in data_val.items()])


def check_str_str_list_of_str_dict(data_val) -> bool:
    if not isinstance(data_val, dict):
        return False
    keys = list(data_val.keys())
    vals = list(list(data_val.values()))
    return check_list_of_str(data_val=keys) and \
        all([check_str_list_of_str_dict(data_val=val) for val in vals])


def check_str_or_list_of_str(data_val) -> bool:
    return check_str(data_val=data_val) or check_list_of_str(data_val=data_val)


def check_int_or_list_of_int(data_val) -> bool:
    return check_int(data_val=data_val) or check_list_of_int(data_val=data_val)


# generic function to apply a given type checker
def apply_data_type_check(data_type: str, data_val) -> bool:
    if data_type not in CHECK_FUNCTIONS:
        raise Exception(f'Unknown data type for check {data_type} -> STOP')
    if CHECK_FUNCTIONS[data_type] is None:
        raise Exception(f'Function to check data type {data_type} is None (not defined) -> STOP')
    return list(map(CHECK_FUNCTIONS[data_type], [data_val]))[0]


# correspondence between types and associated functions (and additional keyword args when applicable) 
# to be applied for type check
CHECK_FUNCTIONS = {
    CheckerNames.is_dict: check_dict,
    CheckerNames.is_str: check_str,
    CheckerNames.is_int: check_int,
    CheckerNames.is_float: check_float,
    CheckerNames.is_list_of_int: check_list_of_int,
    CheckerNames.is_list_of_str: check_list_of_str,
    CheckerNames.is_none_or_list_of_str: check_none_or_list_of_str,
    CheckerNames.is_dict_str_dict: check_str_dict_dict,
    CheckerNames.is_dict_str_list_of_float: check_str_list_of_float_dict,
    CheckerNames.is_dict_str_list_of_str: check_str_list_of_str_dict,
    CheckerNames.is_dict_str_str: check_str_str_dict,
    CheckerNames.is_dict_str_int: check_str_int_dict,
    CheckerNames.is_two_level_dict_str_str_list_of_str: check_str_str_list_of_str_dict,
    CheckerNames.is_two_level_dict_str_str_str: check_three_level_str_dict,
    CheckerNames.is_str_or_list_of_str: check_str_or_list_of_str,
    CheckerNames.is_int_or_list_of_int: check_int_or_list_of_int
}


def apply_params_type_check(param_obj_dict: dict, types_for_check: Dict[str, str], param_name: str):
    check_errors = []
    for attr_tb_checked, type_for_check in types_for_check.items():
        if attr_tb_checked in param_obj_dict:
            check_result = apply_data_type_check(data_type=type_for_check, data_val=param_obj_dict[attr_tb_checked])
            if not check_result:
                check_errors.append(attr_tb_checked)
    if len(check_errors) > 0:
        print_errors_list(error_name=f'{param_name} JSON data with erroneous types',
                          errors_list=check_errors)
