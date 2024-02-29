"""Entity for a weekly chore."""
from __future__ import annotations

from datetime import date

from dateutil.relativedelta import relativedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import WEEKDAYS

from . import const
from .chore import Chore


class WeeklyChore(Chore):
    """Chore every n weeks, odd weeks or even weeks."""

    __slots__ = "_chore_day", "_first_week", "_period"

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Read parameters specific for Weekly Chore Frequency."""
        super().__init__(config_entry)
        config = config_entry.options
        self._chore_day = config.get(const.CONF_CHORE_DAY, None)
        self._period: int
        self._first_week: int
        config.get(const.CONF_FREQUENCY)
        self._period = config.get(const.CONF_PERIOD, 1)
        self._first_week = config.get(const.CONF_FIRST_WEEK, 1)

    def _add_period_offset(self, start_date: date) -> date:
        return start_date + relativedelta(weeks=self._period)

    def _find_candidate_date(self, day1: date) -> date | None: # 2024-02-26
        """Calculate possible date, for weekly frequency."""
        start_date = self._calculate_schedule_start_date() # 2024-02-27
        start_week = start_date.isocalendar()[1] # 10
        day1 = self.calculate_day1(day1, start_date) # 27
        week = day1.isocalendar()[1] # 10
        weekday = day1.weekday() # 1
        offset = -1
        if (week - start_week) % self._period == 0:  # Chore this week
            if self._chore_day is not None:
                day_index = WEEKDAYS.index(self._chore_day) # 6
                if day_index >= weekday:  # Chore still did not happen
                    offset = day_index - weekday # 5
        iterate_by_week = 7 - weekday + WEEKDAYS.index(self._chore_day)
        while offset == -1:  # look in following weeks
            candidate = day1 + relativedelta(days=iterate_by_week)
            week = candidate.isocalendar()[1]
            if (week - start_week) % self._period == 0:
                offset = iterate_by_week
                break
            iterate_by_week += 7
        return day1 + relativedelta(days=offset)
