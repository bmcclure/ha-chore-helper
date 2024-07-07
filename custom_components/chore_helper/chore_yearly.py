"""Entity for a yearly chore."""

from __future__ import annotations

from datetime import date, datetime

from dateutil.relativedelta import relativedelta
from homeassistant.config_entries import ConfigEntry

from . import const
from .chore import Chore


class YearlyChore(Chore):
    """Chore every year."""

    __slots__ = (
        "_period",
        "_date",
    )

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Read parameters specific for Yearly Chore Frequency."""
        super().__init__(config_entry)
        config = config_entry.options
        self._period = config.get(const.CONF_PERIOD, 1)
        due_date = config.get(const.CONF_DATE, None)
        self._date = due_date if due_date is not None and due_date != "0" else None

    def _add_period_offset(self, start_date: date) -> date:
        return start_date + relativedelta(years=self._period)

    def _find_candidate_date(self, day1: date) -> date | None:
        """Calculate possible date, for yearly frequency."""
        start_date = self._calculate_schedule_start_date()
        day1 = self.calculate_day1(day1, start_date)
        conf_date = self._date
        if conf_date is None or conf_date == "":
            conf_date = start_date
        else:
            conf_date = datetime.strptime(conf_date, "%m/%d")
        candidate_date = date(day1.year, conf_date.month, conf_date.day)
        if candidate_date < day1:
            candidate_date = date(day1.year + 1, conf_date.month, conf_date.day)
        difference = abs(candidate_date.year - start_date.year)
        if difference > 0:
            remainder = difference % self._period
            if remainder > 0:
                candidate_date = date(
                    int(candidate_date.year + (self._period - remainder)),
                    candidate_date.month,
                    candidate_date.day,
                )
        return candidate_date
