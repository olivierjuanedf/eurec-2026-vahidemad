import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Union

import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta

from common.constants.optimisation import WHOLE_PERIOD_GRANULARITY
from common.constants.temporal import Timescale
from utils.basic_utils import get_default_values
from utils.dates import get_n_days_in_period, get_n_weeks_in_period, get_n_months_in_period, get_n_days_in_month, \
    timestamp_to_datetime


@dataclass
class Timeseries:
    timescale: str
    value: Union[float, np.ndarray]
    # list of dates corresponding to value vectors; value[i] being for [dates[i], dates[i+1][
    dates: List[datetime] = None

    def check(self, period_start: datetime, period_end: datetime, with_whole_period_gran: bool = False):
        allowed_timescales = get_default_values(obj=Timescale)
        # add whole period "granularity"? In this case value must be of length 1
        if with_whole_period_gran:
            allowed_timescales.append(WHOLE_PERIOD_GRANULARITY)
        # that timescale be in the list of allowed ones
        if self.timescale not in allowed_timescales:
            raise Exception(f'Timeseries with non-allowed timescale {self.timescale}; '
                            f'it must be in {allowed_timescales}')

        # if array value, check its size
        if isinstance(self.value, np.ndarray):
            timescale_to_func = {
                Timescale.day: get_n_days_in_period,
                Timescale.week: get_n_weeks_in_period,
                Timescale.month: get_n_months_in_period,
            }
            if self.timescale == WHOLE_PERIOD_GRANULARITY:
                n_ts_in_period = 1
            else:
                n_ts_in_period = timescale_to_func.get(self.timescale)(start=period_start, end=period_end)
            len_value = len(self.value)
            if not len_value == n_ts_in_period:
                raise Exception(f'Timesrie value has length {len_value}, but must be {n_ts_in_period} to be coherent '
                                f'with start {period_start: %Y/%m/%d}, end {period_end: %Y/%m/%d} and timescale '
                                f'{self.timescale}')

    def set_dates(self, period_start: datetime, period_end: datetime):
        if self.dates is not None:
            logging.warning(f'Timeseries dates will be overwritten based on period start/end '
                            f'and timescale {self.timescale}')
        if self.timescale in [Timescale.day, Timescale.week]:
            period_start_day = datetime(year=period_start.year, month=period_start.month, day=period_start.day)
            period_end_day = datetime(year=period_end.year, month=period_end.month, day=period_end.day)
            start_date = period_start_day
            end_date = period_end_day
            # Weekly timescale: start (resp. end) date is Monday preceding (resp. just after) period start (resp. end)
            if self.timescale == Timescale.week:
                start_date -= timedelta(days=period_start.isoweekday() - 1)
                end_date += timedelta(days=(8 - period_end.isoweekday()) % 7)
        elif self.timescale == Timescale.month:  # first day of month of period_start
            start_date = datetime(year=period_start.year, month=period_start.month, day=1)
            end_date = datetime(year=period_end.year, month=period_end.month, day=1)
            # 1st of next month if period_end not start of a month
            if not period_end.day == 1:
                end_date += relativedelta(months=1)
        # easy using date range...
        if self.timescale in [Timescale.day, Timescale.week]:
            range_freq = '1d' if self.timescale == Timescale.day else '7d'
            period_date_range = pd.date_range(start=start_date, end=end_date, freq=range_freq).to_list()
            period_date_range = [timestamp_to_datetime(my_date=date) for date in period_date_range]
        # looping on dates with 1-month relativedelta
        elif self.timescale == Timescale.month:
            period_date_range = [start_date]
            current_date = start_date
            while current_date + relativedelta(months=1) <= end_date:
                current_date += relativedelta(months=1)
                period_date_range.append(current_date)
        # set dates as date range
        self.dates = period_date_range
        # then correct first/last
        self.dates[0] = period_start
        self.dates[-1] = period_end

    def weigh_values(self, period_start: datetime, period_end: datetime):
        """
        Apply weight to first and last element in value, to account for possibly uncomplete timescale
        :param period_start: start of the period (included)
        :param period_end: end of the period, NOT included
        """
        if self.timescale == Timescale.day:
            start_hour = period_start.hour
            if start_hour > 0:
                first_weight = (24 - start_hour) / 24
            else:
                first_weight = 1
            end_hour = period_end.hour
            # end hour not included -> if 0 the first one of next day;
            # otherwise nber of hours in considered days is end_hour
            if len(self.value) > 1 and end_hour > 0:
                last_weight = end_hour / 24
            else:
                last_weight = 1
        elif self.timescale == Timescale.week:
            start_isoweekday = period_start.isoweekday()  # assumption that hour is always 0
            if not start_isoweekday == 1:  # not a Monday
                first_weight = (8 - start_isoweekday) / 7
            else:
                first_weight = 1
            end_isoweekday = period_end.isoweekday()
            # end day not included -> if 1 the first one (Monday) of next week;
            # otherwise nber of days in considered last week is end_isoweekday - 1
            if len(self.value) > 1 and end_isoweekday > 1:
                last_weight = (end_isoweekday - 1) / 7
            else:
                last_weight = 1
        elif self.timescale == Timescale.month:
            start_day = period_start.day
            # if start day is not 1st in calendar of current month, count nber of days in month from start one
            if not start_day == 1:
                n_days_in_month_start = get_n_days_in_month(year=period_start.year, month=period_start.month)
                first_weight = (n_days_in_month_start - start_day + 1) / n_days_in_month_start
            else:
                first_weight = 1
            end_day = period_end.day
            n_days_in_month_end = get_n_days_in_month(year=period_end.year, month=period_end.month)
            # if end day is not last in calendar of current month, count nber of days
            # strictly before from 1st one in current month
            if not end_day == n_days_in_month_end:
                last_weight = (end_day - 1) / n_days_in_month_end
            else:
                last_weight = 1
        # apply obtained weights for first and last time-slots
        first_value_weighted = round(self.value[0] * first_weight, 2)
        last_value_weighted = round(self.value[-1] * last_weight, 2)
        self.value[0] = first_value_weighted
        self.value[-1] = last_value_weighted
