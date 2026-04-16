import logging
from calendar import calendar
from datetime import datetime, date, timedelta
from typing import List, Optional, Union
from math import ceil

import pandas as pd

from common.constants.temporal import DAY_OF_WEEK
from common.long_term_uc_io import DATE_FORMAT_PRINT

ALLOWED_DATE_FMTS = ['%Y/%m/%d', '%m/%d', '%Y-%m-%d', '%m-%d']
DAY_EXP = {0: 'th', 1: 'st', 2: 'nd', 3: 'rd', 4: 'th', 5: 'th', 6: 'th', 7: 'th', 8: 'th', 9: 'th'}
MONTHS_SHORT = {'January': 'Jan.', 'February': 'Feb.', 'March': 'March', 'April': 'April', 'May': 'May', 'June': 'June',
                'July': 'July', 'August': 'Aug.', 'September': 'Sept.', 'October': 'Oct.', 'November': 'Nov.',
                'December': 'Dec.'}


def set_year_in_date(my_date: datetime, new_year: int) -> datetime:
    return datetime(year=new_year, month=my_date.month, day=my_date.day,
                    hour=my_date.hour, minute=my_date.minute, second=my_date.second)


def remove_useless_zero_in_date(my_date: str, date_sep: str = '/') -> str:
    suppr_first_char = False
    if my_date.startswith('0'):
        my_date = date_sep + my_date
        suppr_first_char = True
    chars_tb_replaced = {f'{date_sep}0{i + 1}': f'{date_sep}{i + 1}' for i in range(9)}
    for old_char, new_char in chars_tb_replaced.items():
        if old_char in my_date:
            my_date = my_date.replace(old_char, new_char)
    if suppr_first_char:
        my_date = my_date[1:]
    return my_date


def add_day_exponent(my_date: str) -> str:
    my_date += DAY_EXP[int(my_date[-1])]
    return my_date


def set_month_short_in_date(my_date: str) -> str:
    for month, month_short in MONTHS_SHORT.items():
        if month in my_date:
            my_date = my_date.replace(month, month_short)
    return my_date


def timestamp_to_datetime(my_date: pd.Timestamp) -> datetime:
    return my_date.to_pydatetime()


def set_temporal_period_str(min_date: datetime, max_date: datetime, print_year: bool, min_str_fmt: bool = True,
                            date_sep: str = '/', rm_useless_zeros: bool = True, in_letter: bool = False,
                            short_months: bool = True, add_day_exp: bool = True) -> str:
    full_date_fmt = f'%Y %B %d' if in_letter else f'%Y{date_sep}%m{date_sep}%d'
    date_wo_year_fmt = f'%B %d' if in_letter else f'%m{date_sep}%d'
    date_with_only_day_fmt = '%d'
    sep_str = '-'
    if sep_str == date_sep:
        sep_str = 'to'

    # set min date as str
    min_date_fmt = full_date_fmt if print_year else date_wo_year_fmt
    min_date_str = min_date.strftime(format=min_date_fmt)
    if rm_useless_zeros:
        min_date_str = remove_useless_zero_in_date(my_date=min_date_str, date_sep=date_sep)

    # idem for max date, with more cases...
    # provide str with full date if
    # (i) not 'min str fmt' requested and print year or
    # (ii) print year and max date year > min date one
    if (not min_str_fmt and print_year) or (print_year and max_date.year > min_date.year):
        max_date_fmt = full_date_fmt if print_year else date_wo_year_fmt
    # with month and day only if
    # (i) not min str fmt and not print year or
    # (ii) not print year or
    # (iii) print year and same year for min and max dates in case of min str fmt requested
    elif not min_str_fmt or max_date.month > min_date.month:
        max_date_fmt = date_wo_year_fmt
    # with day only in other cases i.e., not min str fmt, and same year and month for min and max dates
    else:
        max_date_fmt = date_with_only_day_fmt

    max_date_str = max_date.strftime(format=max_date_fmt)
    if rm_useless_zeros:
        max_date_str = remove_useless_zero_in_date(my_date=max_date_str, date_sep=date_sep)

    # use shortened names, day exponents for months
    if in_letter:
        if short_months:
            min_date_str = set_month_short_in_date(my_date=min_date_str)
            max_date_str = set_month_short_in_date(my_date=max_date_str)
        if add_day_exp:
            min_date_str = add_day_exponent(my_date=min_date_str)
            max_date_str = add_day_exponent(my_date=max_date_str)

    return f'{min_date_str}{sep_str}{max_date_str}'


def get_period_str(period_start: datetime, period_end: datetime) -> str:
    dow_start = DAY_OF_WEEK[period_start.isoweekday()]
    dow_end = DAY_OF_WEEK[period_end.isoweekday()]
    period_start_str = f'{dow_start} {period_start.strftime(DATE_FORMAT_PRINT)}'
    period_end_str = f'{dow_end} {period_end.strftime(DATE_FORMAT_PRINT)}'
    return f'[{period_start_str}, {period_end_str}]'


def robust_date_parser(my_date: str, allowed_formats: List[str] = None,
                       raise_warning: bool = False) -> Optional[datetime]:
    """
    N.B. When no year defined in date format, the default year value set in datetime is 1900 -> coherently with the
    usage of fictive 1900 calendar in this project!
    """
    if allowed_formats is None:
        allowed_formats = ALLOWED_DATE_FMTS

    timezone_str = '+00:00'
    if timezone_str in my_date:
        my_date = my_date.replace(timezone_str, '')
    for date_format in allowed_formats:
        try:
            return datetime.strptime(my_date, date_format)
        except ValueError:
            pass
    if raise_warning:
        logging.warning(f'{my_date} cannot be cast as datetime with list of allowed formats {allowed_formats}'
                        f' -> None returned')
    return None


def set_date_from_year_and_iso_idx(year: int, week_idx: int, day_idx: int = 1, to_datetime: bool = True) \
        -> Union[datetime, date]:
    iso_date = date.fromisocalendar(year, week_idx, day_idx)
    if not to_datetime:
        return iso_date
    return datetime.combine(iso_date, datetime.min.time())


def set_date_from_year_and_day_idx(year: int, day_idx: int) -> datetime:
    return datetime(year, 1, 1) + timedelta(days=day_idx - 1)


def get_n_days_in_period(start: datetime, end: datetime) -> int:
    """
    Number of days in period, both start and end being included in it
    """
    return (end - start).days + 1


def get_n_weeks_in_period(start: datetime, end: datetime) -> int:
    """
    Number of weeks in period, both start and end being included in it
    """
    return ceil((end - start).days / 7)


def get_n_months_in_period(start: datetime, end: datetime) -> int:
    """
    Number of months in period, both start and end being included in it
    """
    return end.month - start.month + 1


def get_n_days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]
