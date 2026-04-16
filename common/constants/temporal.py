from dataclasses import dataclass
from datetime import datetime


DATE_FORMAT_IN_JSON = '%Y/%m/%d'
DAY_OF_WEEK = {1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thur', 5: 'Fri', 6: 'Sat', 7: 'Sun'}
# first date in ERAA data (fictive 364 days calendar)
MIN_DATE_IN_DATA = datetime(year=1900, month=1, day=1)
# first date NOT in ERAA data (fictive 364 days calendar)
MAX_DATE_IN_DATA = datetime(year=1901, month=1, day=1)
N_DAYS_DATA_ANALYSIS_DEFAULT = 14
N_DAYS_UC_DEFAULT = 9


@dataclass
class Timescale:
    day: str = 'day'
    week: str = 'week'
    month: str = 'month'
