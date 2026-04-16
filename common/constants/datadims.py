from dataclasses import dataclass


@dataclass
class DataDimensions:
    agg_prod_type: str = 'agg_prod_type'
    year: str = 'year'
    climatic_year: str = 'climatic_year'
    zone: str = 'zone'
    extra_args: str = 'extra_args'
