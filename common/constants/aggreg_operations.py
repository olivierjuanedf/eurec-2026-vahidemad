from dataclasses import dataclass


@dataclass
class AggregOpeNames:
    mean: str = 'mean'
    sum: str = 'sum'
    