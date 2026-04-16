import logging
from datetime import datetime
from typing import List, Dict

from include.dataset_builder import PypsaModel


# TODO: heritage? Per type of stress test
class StressTest:
    def __init__(self, name: str, countries: List[str] = None, per_country_prod_types: Dict[str, List[str]] = None,
                 start_date: datetime = None, end_date: datetime = None):
        self.name = name
        self.countries = countries
        self.start_date = start_date  # default will be to apply stress test to whole UC model period
        self.end_date = end_date

    def process(self, all_countries: List[str], uc_dates: List[datetime]):
        # stress test to be applied to all countries
        if self.countries == ['europe']:
            self.countries = all_countries
        if self.start_date is None:
            self.start_date = min(uc_dates)
        if self.end_date is None:
            self.end_date = max(uc_dates)

    def apply(self, pypsa_model: PypsaModel) -> PypsaModel:
        """
        Apply stress test to PypsaModel -> on generators, interconnections, etc.
        """
        logging.info(f'Apply stress test {self.name} on PyPSA model {pypsa_model.name}')
        return pypsa_model
