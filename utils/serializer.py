from typing import Union

import numpy as np


def array_serializer(my_array: np.ndarray, stat_repres: bool = False) -> Union[list, dict]:
    # calculate some stat. metrics to "represent" considered vector
    if stat_repres:
        return {'min': my_array.min(), 'max': my_array.max(), 'mean': my_array.mean(), 'std': my_array.std()}
    return list(my_array)
