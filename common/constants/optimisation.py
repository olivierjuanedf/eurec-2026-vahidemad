import logging
from dataclasses import dataclass
from typing import List

import numpy as np

from common.constants.countries import set_country_trigram
from common.constants.temporal import Timescale
from common.error_msgs import print_errors_list, unknown_value_error
from utils.basic_utils import format_with_spaces, get_repeated_elts_in_lst, get_default_values


@dataclass
class OptimSolvers:
    gurobi: str = 'gurobi'
    highs: str = 'highs'


@dataclass
class OptimPbTypes:
    lp: str = 'lp'
    milp: str = 'milp'
    qp: str = 'qp'
    miqp: str = 'miqp'


@dataclass
class OptimPbCharacteristics:
    type: str = 'LP'
    n_variables: int = None
    n_int_variables: int = None
    n_constraints: int = None

    def __repr__(self) -> str:
        repr_str = f'{self.type.upper()} optimisation pb with:'
        repr_str += f'\n* {format_with_spaces(number=self.n_variables)} variables'
        if self.n_int_variables is not None:
            repr_str += f' (including {format_with_spaces(number=self.n_int_variables)} integer ones)'
        repr_str += f'\n* {format_with_spaces(number=self.n_constraints)} constraints'
        return repr_str


@dataclass
class OptimResolStatus:
    optimal: str = 'optimal'
    infeasible: str = 'infeasible'


OPTIM_RESOL_STATUS = OptimResolStatus()


@dataclass
class SolverParams:
    name: str = 'highs'
    license_file: str = None


DEFAULT_OPTIM_SOLVER_PARAMS = SolverParams(name=OptimSolvers.highs)


@dataclass
class CustomConstraintNames:
    max_co2_emissions: str = 'max_co2_emissions'


@dataclass
class CustomConstraintDirection:
    upper: str = 'upper'
    lower: str = 'lower'
    equal: str = 'equal'


@dataclass
class ConstMultCoeffNames:
    variable_cost: str = 'variable_cost'
    co2_emis_factor: str = 'co2_emis_factor'


# TODO: put as object (below) constants?
N_COUNTRIES_MAX_IN_NAME = 3
WHOLE_PERIOD_GRANULARITY: str = 'whole_period'


@dataclass
class ZoneAndTempProdSumConstraint:
    """
    Zone (z) and temporal (t) sum of production constraint objects, of the form:
    sum_{z, t} prod(z, t) * coeff(z, t) <= ub (or >= lb)
    with coeff passed as a name of attribute available in PyPSA model defined here, variable_cost or co2_emis_factor
    """
    type: str  # name of the type of constraint, e.g. co2_emis
    # either upper (zone-and-temp sum prod. <= bound) or lower (zone-and-temp sum prod. >= bound) or equal
    # (idem = bound)
    direction: str
    mult_coeff_name: str  # name of the multiplicative coeffs to be used
    temporal_granularity: str  # temporal granularity associated to this constraint
    countries: List[str]  # over which constraints is to be imposed
    bound: np.ndarray
    name: str = None

    def __repr__(self) -> str:
        attr_sep = '\n- '
        repr_str = f'{self.type} zone-and-temp. production-sum constraint'
        repr_str += f' ({self.direction} bound)'
        repr_str += f'{attr_sep}with {self.mult_coeff_name} multiplicative coeffs'
        if self.name is None:
            self.set_name()
        repr_str += f'{attr_sep}over {self.name}'
        repr_str += f'{attr_sep}and with temp. granularity {self.temporal_granularity}'
        return repr_str

    def set_name(self):
        n_countries = len(self.countries)
        if n_countries <= N_COUNTRIES_MAX_IN_NAME:
            country_trigrams = [set_country_trigram(elt) for elt in self.countries]
            self.name = '-'.join(country_trigrams)
        else:
            self.name = f'{n_countries}-countries'

    def process(self):
        # add name if not provided
        if self.name is None:
            self.set_name()

    def check(self, available_countries: List[str]):
        const_def_errors = []
        # 1. All known countries?
        unknown_countries = list(set(self.countries) - set(available_countries))
        if len(unknown_countries) > 0:
            logging.warning(f'Unknown countries in {str(self)} arg: {unknown_countries}'
                            f'\n-> will not be accounted for in this constraint')
            self.countries = [elt for elt in self.countries if elt in available_countries]
        # 2. Repeated countries associated to this constraint?
        repeated_countries = get_repeated_elts_in_lst(my_lst=self.countries)
        if len(repeated_countries) > 0:
            logging.warning(f'There are repeated countries in {str(self)}: {repeated_countries}\n'
                            f'-> will be counted only once in this constraint rhs CO2 emis. calculation')
            self.countries = list(set(self.countries))
        # 3.-5. Known temporal granularity - 'direction' for the constraint - multiplicative coeff. name
        # first set/get available values for these 3 attrs
        # -> stop with error if not valid
        available_temp_granularities = get_default_values(obj=Timescale)
        # add 'granularity' corresponding to the application of this constraint to whole period
        available_temp_granularities.append(WHOLE_PERIOD_GRANULARITY)
        avail_const_directions = get_default_values(obj=CustomConstraintDirection)
        avail_mult_coeff_names = get_default_values(obj=ConstMultCoeffNames)
        known_value_checks = {'temporal granularity': (self.temporal_granularity, available_temp_granularities),
                              'constraint "direction"': (self.direction, avail_const_directions),
                              'multiplicative coeff. name': (self.mult_coeff_name, avail_mult_coeff_names)}
        for attr_name, (val, avail_vals) in known_value_checks.items():
            if val not in avail_vals:
                const_def_errors.append(unknown_value_error(var_name=attr_name, value=val,
                                                            available_values=avail_vals)
                                        )

        if len(const_def_errors) > 0:
            print_errors_list(error_name=f'in {str(self)}', errors_list=const_def_errors)
