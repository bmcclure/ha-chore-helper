"""Entity for a daily chore."""

from __future__ import annotations

from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from homeassistant.config_entries import ConfigEntry

from . import const
from .chore import Chore


class DailyChore(Chore):
    """Chore every n days."""

    __slots__ = ("_period",)

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Read parameters specific for Daily Chore Frequency."""
        super().__init__(config_entry)
        config = config_entry.options
        self._period = config.get(const.CONF_PERIOD)

    def _add_period_offset(self, start_date: date) -> date:
        return start_date + timedelta(days=self._period)

    def _find_candidate_date(self, day1: date) -> date | None:
        """Calculate possible date, for every-n-days and after-n-days frequency."""
        schedule_start_date = self._calculate_schedule_start_date()
        day1 = self.calculate_day1(day1, schedule_start_date)

        try:
            remainder = (day1 - schedule_start_date).days % self._period  # type: ignore
            if remainder == 0:
                return day1
            offset = self._period - remainder
        except TypeError as error:
            raise ValueError(
                f"({self._attr_name}) Please configure start_date and period "
                "for every-n-days or after-n-days chore frequency."
            ) from error

        return day1 + relativedelta(days=offset)
