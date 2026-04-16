from typing import Dict, List, Tuple, Union

from common.long_term_uc_io import INTERCO_STR_SEP


def set_interco_to_tuples(interco_names: str, return_corresp: bool = False) \
        -> Union[Dict[str, Tuple[str]], List[Tuple[str]]]:
    if return_corresp:
        return {interco: tuple(interco.split(INTERCO_STR_SEP)) for interco in interco_names}
    else:
        return [tuple(interco.split(INTERCO_STR_SEP)) for interco in interco_names]
    