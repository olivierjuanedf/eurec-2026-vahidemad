import logging
from typing import List, Optional, Tuple, Union, Dict
import numpy as np
import math
from dataclasses import fields, MISSING
from collections import Counter


CLIM_YEARS_SUFFIX = 'clim-years'  # TODO: set this constant in a more logical place... constant\...


def str_sanitizer(raw_str: Optional[str], replace_empty_char: bool = True,
                  ad_hoc_replacements: dict = None) -> Optional[str]:
    # sanitize only if str
    if not isinstance(raw_str, str):
        return raw_str

    sanitized_str = raw_str
    sanitized_str = sanitized_str.strip()
    if replace_empty_char:
        sanitized_str = sanitized_str.replace(' ', '_')
    sanitized_str = sanitized_str.lower()

    # if specific replacements to be applied
    if ad_hoc_replacements is not None:
        for old_char, new_char in ad_hoc_replacements.items():
            sanitized_str = sanitized_str.replace(old_char, new_char)
    return sanitized_str


def rm_elts_with_none_val(my_dict: dict) -> dict:
    return {key: val for key, val in my_dict.items() if val is not None}


def get_key_of_val(val, my_dict: dict, dict_name: str = None):
    corresp_keys = []
    for key in my_dict:
        if val in my_dict[key]:
            corresp_keys.append(key)
    if dict_name is None:
        dict_name = ''
    else:
        dict_name = f' {dict_name}'
    if len(corresp_keys) == 0:
        logging.warning(f'No corresponding key found in {dict_name} dict. for value {val} -> None returned')
        return None
    if len(corresp_keys) > 1:
        logging.warning(f'Multiple corresponding keys found in{dict_name} dict. for value {val} '
                        f'-> only first one returned')
    return corresp_keys[0]


def is_str_bool(bool_str: Optional[str]) -> bool:
    if not isinstance(bool_str, str):
        return False
    return bool_str.lower() in ['true', 'false']


def cast_str_to_bool(bool_str: str) -> Optional[bool]:
    bool_str = bool_str.lower()
    if bool_str == 'true':
        return True
    if bool_str == 'false':
        return False
    return None


def robust_cast_str_to_float(float_str: str) -> Optional[float]:
    try:
        return float(float_str)
    except:
        return None


def are_lists_eq(list_of_lists: List[list]) -> bool:
    first_list = list_of_lists[0]
    len_first_list = len(first_list)
    set_first_list = set(first_list)
    n_lists = len(list_of_lists)
    for i_list in range(1, n_lists):
        current_list = list_of_lists[i_list]
        if not (len(current_list) == len_first_list and set(current_list) == set_first_list):
            return False
    return True


def lexico_compar_str(string1: str, string2: str, return_tuple: bool = False) -> Union[str, Tuple[str, str]]:
    i = 0
    while i < len(string1) and i < len(string2):
        if string1[i] < string2[i]:
            return (string1, string2) if return_tuple else string1
        elif string1[i] > string2[i]:
            return (string2, string1) if return_tuple else string2
        i += 1
    # one of the strings starts with the other
    if len(string2) > len(string1):
        return (string1, string2) if return_tuple else string1
    else:
        return (string2, string1) if return_tuple else string2


def flatten_list_of_lists(list_of_lists: list) -> list:
    return np.concatenate(list_of_lists).tolist()


def get_intersection_of_lists(list1: list, list2: list) -> list:
    return list(set(list1) & set(list2))


def get_repeated_elts_in_lst(my_lst: list) -> list:
    counter = Counter(my_lst)
    return [item for item, count in counter.items() if count > 1]


def set_years_suffix(years: List[int], is_climatic_year: bool = False, sep: str = '-') -> str:
    n_years = len(years)
    if n_years == 0:
        return ''
    if n_years == 1:
        return f'{years[0]}'
    if n_years == 2:
        min_date = f'{min(years)}'
        max_date = f'{max(years)}'
        if min_date[:2] == max_date[:2]:
            return f'{min_date}{sep}{max_date[2:]}'
        else:
            return f'{min_date}{sep}{max_date}'
    suffix = CLIM_YEARS_SUFFIX if is_climatic_year else 'years'
    return f'{n_years}{sep}{suffix}'


def lowest_common_multiple(a, b):
    return abs(a * b) // math.gcd(a, b)


def print_non_default(obj, msg_if_all_defaults: bool = True, obj_name: str = None, log_level: str = 'info'):
    non_default_msg = ''
    sep = '\n- '
    for f in fields(obj):
        default = f.default if f.default is not MISSING else None
        value = getattr(obj, f.name)
        if value != default:
            non_default_msg += f"{sep}{f.name} = {value}"
    # set log msg
    log_msg = None
    if len(non_default_msg) > 0:
        obj_name_suffix = f' for object {obj_name}' if obj_name is not None else ''
        log_msg = f'Non-default attrs used{obj_name_suffix}:{non_default_msg}'
    elif msg_if_all_defaults:
        log_msg = 'All default values used'

    # print it out at proper log level
    if log_msg is not None:
        if log_level == 'info':
            logging.info(log_msg)
        elif log_level == 'debug':
            logging.debug(log_level)


def get_all_attr_names(obj) -> List[str]:
    return [f.name for f in fields(obj)]


def get_default_values(obj) -> list:
    return [f.default if f.default is not MISSING else f.default_factory() for f in fields(obj)
            if f.default is not MISSING or f.default_factory is not MISSING]


def get_first_level_with_multiple_vals(tuple_list: List[tuple], init_level: int = None,
                                       return_none_if_not_found: bool = False) -> Optional[int]:
    if init_level is None:
        init_level = 0
    n_levels = len(tuple_list[0])
    i_level = init_level
    while i_level < n_levels:
        current_values = set([elt[i_level] for elt in tuple_list])
        if len(current_values) > 1:
            return i_level
        i_level += 1
    if return_none_if_not_found:
        return None
    return n_levels


def random_draw_in_list(my_list: list):
    n_elts = len(my_list)
    i_rand = np.random.randint(n_elts)
    return my_list[i_rand]


def endswith_in_list(my_str: str, end_elts: List[str]) -> bool:
    for elt in end_elts:
        if my_str.endswith(elt):
            return True
    return False


def rm_elts_in_str(my_str: str, elts_tb_removed: List[str]) -> str:
    for elt in elts_tb_removed:
        if elt in my_str:
            my_str = my_str.replace(elt, '')
    return my_str


def sort_lexicographically(strings: list[str]) -> list[str]:
    return sorted(strings)


def check_all_values_equal(d: dict) -> bool:
    """
    Check that all values in a nested dict. are equal
    """
    values = []

    def traverse(obj):
        if isinstance(obj, dict):
            for v in obj.values():
                traverse(v)
        else:
            values.append(obj)

    traverse(d)
    return all([elt == values[0] for elt in values])


def format_with_spaces(number) -> str:
    return f"{number:,}".replace(",", " ")


def dict_to_str(d: Dict[str, float], nbers_with_spaces: bool = False) -> str:
    """
    Nice printing of dictionary into logs
    """
    str_sep = ', '
    if nbers_with_spaces:
        key_val_lst = [f'{key}: {format_with_spaces(number=val)}' for key, val in d.items()]
    else:
        key_val_lst = [f'{key}: {val}' for key, val in d.items()]
    return str_sep.join(key_val_lst)