from typing import Dict, List

from common.fuel_sources import FuelSource


gps_coords = (0, 0)  # Your choice!


def get_generators(country_trigram: str, fuel_sources: Dict[str, FuelSource],
                   wind_onshore_data, wind_offshore_data, solar_pv_data) -> List[dict]:
    """
    Get list of generators to be set on a given node of a PyPSA model
    :param country_trigram: name of considered country, as a trigram (ex: "ben", "fra", etc.)
    :param fuel_sources
    """
    # List to be completed
    generators = []
    return generators
