import logging

from dataclasses import dataclass
from typing import Dict, List, Union, Optional, Tuple

from common.constants.datadims import DataDimensions
from common.constants.plots import PlotNames
from common.constants.prod_types import STOCK_LIKE_PROD_TYPES, add_suffix_to_storage_unit_col
from utils.basic_utils import get_default_values


def to_int_keys_dict(dict_with_level_two_str_keys: Dict[str, Dict[str, str]]) -> Optional[Dict[str, Dict[int, str]]]:
    if dict_with_level_two_str_keys is None:
        return None
    return {name: {int(key): value for key, value in dict_with_str_keys.items()}
            for name, dict_with_str_keys in dict_with_level_two_str_keys.items()}


OWN_PALETTE = 'own'
DEFAULT_PLOT_DIMS_ORDER = [DataDimensions.zone, DataDimensions.agg_prod_type, DataDimensions.year,
                           DataDimensions.climatic_year, DataDimensions.extra_args]
TYPE_PARAMS_DEF = Union[Dict[str, Dict[str, str]], Dict[str, Dict[int, str]]]
TYPE_PER_CASE_PARAMS = Union[Dict[str, str], Dict[int, str]]
N_LETTERS_ZONE = 3
N_MAX_CHARS_FLAT_LABEL = 8


@dataclass
class PlotParamsKeysInJson:  # names of (some of) the keys in \input\functional\plot_params.json
    fig_style: str = 'fig_style'
    plots_tb_done: str = 'plots_tb_done'


def set_per_case_dict(params_def: TYPE_PARAMS_DEF, param_choice: str,
                      param_name: str) -> Optional[TYPE_PER_CASE_PARAMS]:
    if params_def is None:
        return None
    if param_choice in params_def:
        return params_def[param_choice]
    else:
        logging.warning(
            f'{param_name.capitalize()} choice {param_choice} not in {param_name} def. {params_def} '
            f'-> cannot be accounted for in PlotParams')
        return None


@dataclass
class PlotParams:
    dimension: str = None
    # first parameters to set up a choice of parameters for a given execution
    palette_choice: str = OWN_PALETTE
    linestyle_choice: str = OWN_PALETTE
    marker_choice: str = OWN_PALETTE
    order: Union[List[str], List[int]] = None
    # remaining ones for the def of the different possible values for the parameters
    # {name of the palette: {zone name/agg. prod. type/year/climatic year: color}}.
    # N.B. (climatic) year in str when parsing json; in int after processing
    palettes_def: TYPE_PARAMS_DEF = None
    # Idem palettes_def
    linestyles_def: TYPE_PARAMS_DEF = None
    # Idem palettes_def
    markers_def: TYPE_PARAMS_DEF = None
    # simpler dicts, obtained based on choice + def.
    per_case_color: TYPE_PER_CASE_PARAMS = None
    per_case_linestyle: TYPE_PER_CASE_PARAMS = None
    per_case_marker: TYPE_PER_CASE_PARAMS = None

    def process(self):
        # convert str to int keys
        num_plot_dims = [DataDimensions.year, DataDimensions.climatic_year, DataDimensions.extra_args]
        if self.dimension in num_plot_dims:
            self.palettes_def = to_int_keys_dict(dict_with_level_two_str_keys=self.palettes_def)
            self.linestyles_def = to_int_keys_dict(dict_with_level_two_str_keys=self.linestyles_def)
            self.markers_def = to_int_keys_dict(dict_with_level_two_str_keys=self.markers_def)

        # from choice and def. to simpler dicts
        self.per_case_color = set_per_case_dict(params_def=self.palettes_def, param_choice=self.palette_choice,
                                                param_name='palette')
        self.per_case_linestyle = set_per_case_dict(params_def=self.linestyles_def, param_choice=self.linestyle_choice,
                                                    param_name='linestyle')
        self.per_case_marker = set_per_case_dict(params_def=self.markers_def, param_choice=self.marker_choice,
                                                 param_name='marker')

        # set order for numeric idx, if not already provided
        if self.dimension in num_plot_dims and self.order is None:
            self.order = list(self.per_case_color)
            self.order.sort()

    def check(self, json_plot_params_file: str):
        # TODO: check TB coded
        bob = 1
        # logging.warning('Plot params check TO BE CODED')

    def add_colors_for_stock_with_suffix(self):
        """
        During the execution of the code if both prod. and cons. of stock-like assets are plotted on the same graph,
        the color dictionary needs to be enriched with - identical - colors for this 'cases with suffix'
        """
        added_colors = {}
        for prod_type, color in self.per_case_color.items():
            if prod_type in STOCK_LIKE_PROD_TYPES:
                added_colors |= {add_suffix_to_storage_unit_col(col=prod_type, col_type='prod'): color,
                                 add_suffix_to_storage_unit_col(col=prod_type, col_type='cons'): color}
        self.per_case_color |= added_colors


@dataclass
class XtickDateFormat:
    dow: str = 'dow'  # day of week H:
    # Year month in letter day H:, wo repeating (year, month, day) if idem to previous xtick
    in_letter: str = 'in_letter'


@dataclass
class CurveStyles:
    absolute: str = 'absolute'
    relative: str = 'relative'


DEFAULT_DATE_XTICK_FMT = XtickDateFormat.in_letter


@dataclass
class FigureStyle:
    size: Tuple[int, int] = (10, 6)
    marker: str = None
    grid_on: bool = True
    tight_x: bool = True
    # curve style def -> 'absolute' to set up (color, linestyle, marker) based on (zone, year, clim year) value
    # whatever content of figure (other curves plotted); 'relative' to define it relatively
    curve_style: str = CurveStyles.absolute
    plot_dims_order: List[str] = None
    # all legend parameters
    print_legend: bool = True
    legend_font_size: int = 15
    legend_loc: str = 'best'
    # xtick (labels)
    delta_xticks: int = None
    date_xtick_fmt: str = XtickDateFormat.in_letter
    add_day_exp_in_date_xtick: bool = False
    rm_useless_zeros_in_date_xtick: bool = True
    date_xtick_fontsize: int = 12
    date_xtick_rotation: int = 45
    n_curves_max: int = 8

    def process(self):
        if self.plot_dims_order is None:
            self.plot_dims_order = DEFAULT_PLOT_DIMS_ORDER
        else:
            unknown_plot_dims = [elt for elt in self.plot_dims_order if elt not in DEFAULT_PLOT_DIMS_ORDER]
            if len(unknown_plot_dims) > 0:
                logging.warning(f'Unknown plot dimensions {unknown_plot_dims} '
                                f'-> default order {DEFAULT_PLOT_DIMS_ORDER} will be used instead')
                self.plot_dims_order = DEFAULT_PLOT_DIMS_ORDER

    def set_print_legend(self, value: bool):
        self.print_legend = value

    def set_add_day_exp(self, value: bool):
        self.add_day_exp_in_date_xtick = value
