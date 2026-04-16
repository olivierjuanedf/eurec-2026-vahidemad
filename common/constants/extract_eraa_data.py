from dataclasses import dataclass
from typing import Dict, List, Tuple, Union, Optional, Literal

from common.constants.usage_params_json import EnvPhaseNames
from utils.basic_utils import is_str_bool, cast_str_to_bool
from utils.eraa_utils import set_interco_to_tuples
from utils.type_checker import apply_params_type_check

FICTIVE_CALENDAR_YEAR = 1900
INTERCO_STR_SEP = '2'

Mode = Literal['solo', 'europe']

# raw types (just after reading) of the following attributes
# -> for 'direct' check to stop asap if erroneous values
# TODO: define complex types in a dataclass (centralized)
RAW_TYPES_FOR_CHECK = {'eraa_dataset_descr':
                           {'aggreg_prod_types_def': 'two_level_dict_str_str_list-of-str',
                            'agg_prod_types_with_cf_data': 'list_of_str',
                            'available_climatic_years': 'list_of_int',
                            'available_countries': 'list_of_str',
                            'available_aggreg_prod_types': 'two_level_dict_str_str_list-of-str',
                            'available_intercos': 'list_of_str',
                            'available_target_years': 'list_of_int',
                            'eraa_edition': 'str',
                            'gps_coordinates': 'dict_str_list_of_float',
                            'pypsa_unit_params_per_agg_pt': 'dict_str_dict',
                            'units_complem_params_per_agg_pt': 'two_level_dict_str_str_str'
                            },
                       'pypsa_static_params':
                           {
                               'min_unit_params_per_agg_pt': 'dict_str_list_of_str'
                           },
                       'plot_params':
                           {
                               'zone_palette_choice': 'str',
                               'agg_prod_type_palette_choice': 'str',
                               'zone_palettes_def': 'two_level_dict_str_str_str',
                               'agg_prod_type_palettes_def': 'two_level_dict_str_str_str'
                           }
                       }


@dataclass
class UsageParameters:
    adding_interco_capas: bool = False
    # apply per country JSON file data selection/overwriting params?
    # N.B. {str: str} in JSON file; {str: bool} after parsing
    apply_per_country_json_file_params: Union[Dict[str, str], Dict[str, bool]] = None
    overwriting_eraa_interco_capa_vals: bool = False
    manually_adding_demand: bool = False
    manually_adding_generators: bool = False
    mode: Mode = 'solo'
    team: Optional[str] = None
    log_level: str = 'info'
    # parameters for climate-based 'sensitivity' tests
    apply_cf_techno_breakthrough: bool = False
    res_cf_stress_test_folder: str = None
    res_cf_stress_test_cy: int = None

    def process(self):
        if self.apply_per_country_json_file_params is None:
            self.apply_per_country_json_file_params = {EnvPhaseNames.data_analysis: False,
                                                       EnvPhaseNames.monozone_toy_uc_model: True,
                                                       EnvPhaseNames.multizones_uc_model: True}
        else:  # from str (in JSON file) to bool
            self.apply_per_country_json_file_params = \
                {phase_name: cast_str_to_bool(bool_str=val)
                 for phase_name, val in self.apply_per_country_json_file_params.items()}

    def check_types(self):
        """
        Check coherence of types
        """
        # TODO: code it


# TODO: "failure" as global constant
FAILURE_ASSET = 'failure'


@dataclass
class ERAADatasetDescr:
    # {datatype: {aggreg. prod. type: list of ERAA prod types}}
    aggreg_prod_types_def: Dict[str, Dict[str, List[str]]]
    agg_prod_types_with_cf_data: List[str]  # list of aggreg. prod types with CF (to be read)
    available_climatic_years: List[int]
    available_countries: List[str]
    available_aggreg_prod_types: Union[Dict[str, Dict[str, List[str]]], Dict[str, Dict[int, List[str]]]]
    available_intercos: Union[List[str], List[Tuple[str, str]]]
    available_target_years: List[int]  # N.B. 'target year' is a 'year' in ERAA terminology
    eraa_edition: str
    # per (meta-)country GPS coordinates - only for network plot
    gps_coordinates: Union[Dict[str, List[float]], Dict[str, Tuple[float, float]]]
    pypsa_unit_params_per_agg_pt: Dict[str, dict]  # dict of per aggreg. prod type main Pypsa params
    # for each aggreg. prod type, a dict. {complem. param name: source - 'from_json_tb_modif'/'from_eraa_data'}
    units_complem_params_per_agg_pt: Dict[str, Dict[str, str]]
    # for a stress test to be done, on an additional set of climatic years
    available_climatic_years_stress_test: List[int] = None

    def check_types(self):
        """
        Check coherence of types
        """
        apply_params_type_check(param_obj_dict=self.__dict__,
                                types_for_check=RAW_TYPES_FOR_CHECK['eraa_dataset_descr'],
                                param_name='ERAA description data - fixed ones -')

    # TODO: get auto_add_failure_pu from global usage params
    def process(self, auto_add_failure_pu: bool = True):
        # convert str bool to boolean
        for agg_pt, pypsa_params in self.pypsa_unit_params_per_agg_pt.items():
            for param_name, param_val in pypsa_params.items():
                if is_str_bool(bool_str=param_val):
                    self.pypsa_unit_params_per_agg_pt[agg_pt][param_name] = bool(param_val)
        for country in self.gps_coordinates:
            self.gps_coordinates[country] = tuple(self.gps_coordinates[country])
        # from '{zone_origin}{INTERCO_STR_SEP}{zone_dest}' format of interco names to tuples (zone_origin, zone_dest)
        self.available_intercos = set_interco_to_tuples(interco_names=self.available_intercos)
        # convert str year values to int
        new_avail_aggreg_pt_dict = {}
        for country, all_years_dict in self.available_aggreg_prod_types.items():
            new_avail_aggreg_pt_dict[country] = {int(elt_year): all_years_dict[elt_year] for elt_year in all_years_dict}
            # and add failure - fictive - asset
            if auto_add_failure_pu:
                for elt_year in new_avail_aggreg_pt_dict[country]:
                    if FAILURE_ASSET not in new_avail_aggreg_pt_dict[country][elt_year]:
                        new_avail_aggreg_pt_dict[country][elt_year].append(FAILURE_ASSET)

        self.available_aggreg_prod_types = new_avail_aggreg_pt_dict
        # replace '.' by '-' in edition
        self.eraa_edition = self.eraa_edition.replace('.', '-')


ALL_UNITS_KEY = 'all_units'


@dataclass
class PypsaStaticParams:
    # per aggreg. prod. unit list of minimal parameters for PyPSA generators to be built
    min_unit_params_per_agg_pt: Dict[str, List[str]]
    generator_params_default_vals: Dict[str, Union[str, float, int]]

    def check_types(self):
        """
        Check coherence of types
        """
        apply_params_type_check(param_obj_dict=self.__dict__,
                                types_for_check=RAW_TYPES_FOR_CHECK['pypsa_static_params'],
                                param_name='PyPSA static params - to set objects main infos')

    def process(self):
        # add common static params to all agg. prod type
        if ALL_UNITS_KEY in self.min_unit_params_per_agg_pt:
            common_min_params = self.min_unit_params_per_agg_pt[ALL_UNITS_KEY]
            self.min_unit_params_per_agg_pt.pop(ALL_UNITS_KEY)
            for agg_pt in self.min_unit_params_per_agg_pt:
                self.min_unit_params_per_agg_pt[agg_pt].extend(common_min_params)
