"""Entity for a monthly chore."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import WEEKDAYS

from . import const
from .chore import Chore


class MonthlyChore(Chore):
    """Chore every nth weekday of each month."""

    __slots__ = (
        "_day_of_month",
        "_chore_day",
        "_monthly_force_week_numbers",
        "_period",
        "_weekday_order_number",
        "_week_order_number",
        "_due_date_offset",
    )

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Read parameters specific for Monthly Chore Frequency."""
        super().__init__(config_entry)
        config = config_entry.options
        day_of_month = config.get(const.CONF_DAY_OF_MONTH)
        self._day_of_month: int | None = (
            int(day_of_month) if day_of_month is not None and day_of_month > 0 else None
        )
        self._chore_day = config.get(const.CONF_CHORE_DAY, None)
        self._monthly_force_week_numbers = config.get(
            const.CONF_FORCE_WEEK_NUMBERS, False
        )
        self._due_date_offset = int(config.get(const.CONF_DUE_DATE_OFFSET, 0))
        self._weekday_order_number: int | None
        self._week_order_number: int | None
        order_number: int = 1
        if const.CONF_WEEKDAY_ORDER_NUMBER in config:
            order_number = int(config[const.CONF_WEEKDAY_ORDER_NUMBER])
        if self._monthly_force_week_numbers:
            self._weekday_order_number = None
            self._week_order_number = order_number
        else:
            self._weekday_order_number = order_number
            self._week_order_number = None
        self._period = config.get(const.CONF_PERIOD, 1)

    @staticmethod
    def viable_weeks_in_month(
        date_of_month: date,
        chore_day: int,
        last_week_must_contain_chore_day: bool = False,
    ) -> int:
        """Find the highest week number that contains the chore day in the month."""
        first_of_month = date(date_of_month.year, date_of_month.month, 1)
        last_of_month = first_of_month + relativedelta(day=31)
        first_week = first_of_month.isocalendar()[1]
        if last_week_must_contain_chore_day:
            last_chore_day_offset = (last_of_month.weekday() - chore_day) % 7
            last_chore_day = last_of_month - timedelta(days=last_chore_day_offset)
            last_chore_week = last_chore_day.isocalendar()[1]
        else:
            last_chore_week = last_of_month.isocalendar()[1]
        return last_chore_week - first_week + 1

    @staticmethod
    def nth_week_date(week_number: int, date_of_month: date, chore_day: int) -> date:
        """Find weekday in the nth week of the month."""
        first_of_month = date(date_of_month.year, date_of_month.month, 1)
        actual_week_number = (
            week_number
            if week_number > 0
            else max(
                MonthlyChore.viable_weeks_in_month(date_of_month, chore_day, False)
                + week_number
                + 1,
                1,
            )
        )

        return first_of_month + relativedelta(
            days=chore_day - first_of_month.weekday() + (actual_week_number - 1) * 7
        )

    @staticmethod
    def nth_weekday_date(
        weekday_number: int, date_of_month: date, chore_day: int
    ) -> date:
        """Find nth weekday of the month."""
        first_of_month = date(date_of_month.year, date_of_month.month, 1)
        actual_weekday_number = (
            weekday_number
            if weekday_number > 0
            else max(
                MonthlyChore.viable_weeks_in_month(date_of_month, chore_day, True)
                + weekday_number
                + 1,
                1,
            )
        )

        # 1st of the month is before the day of chore
        # (so 1st chore week the week when month starts)
        if chore_day >= first_of_month.weekday() or weekday_number < 0:
            return first_of_month + relativedelta(
                days=chore_day
                - first_of_month.weekday()
                + (actual_weekday_number - 1) * 7
            )
        return first_of_month + relativedelta(
            days=7
            - first_of_month.weekday()
            + chore_day
            + (actual_weekday_number - 1) * 7
        )

    def _monthly_candidate(self, day1: date, start_date: date) -> tuple[date, int]:
        """Calculate possible date, for monthly frequency.

        2nd value is the month to consider the date in, even if different.
        """
        if self._chore_day is None:
            day_of_month = self._day_of_month
            if self._day_of_month is None:
                month_range = monthrange(day1.year, day1.month)
                day_of_month = (
                    start_date.day
                    if month_range[1] >= start_date.day
                    else month_range[1]
                )

            if day1.day <= day_of_month:
                return (date(day1.year, day1.month, day_of_month), day1.month)
            if day1.month == 12:
                return (date(day1.year + 1, 1, day_of_month), 1)
            return (date(day1.year, day1.month + 1, day_of_month), day1.month + 1)
        if self._monthly_force_week_numbers:
            if self._week_order_number is not None:
                candidate_date = MonthlyChore.nth_week_date(
                    self._week_order_number, day1, WEEKDAYS.index(self._chore_day)
                )
                # date is today or in the future -> we have the date
                if candidate_date >= day1:
                    return (candidate_date, day1.month)
        else:
            if self._weekday_order_number is not None:
                candidate_date = MonthlyChore.nth_weekday_date(
                    self._weekday_order_number,
                    day1,
                    WEEKDAYS.index(self._chore_day),
                )
                # date is today or in the future -> we have the date
                if candidate_date >= day1:
                    return (candidate_date, day1.month)
        if day1.month == 12:
            next_chore_month = date(day1.year + 1, 1, 1)
        else:
            next_chore_month = date(day1.year, day1.month + 1, 1)
        if self._monthly_force_week_numbers:
            return (
                MonthlyChore.nth_week_date(
                    self._week_order_number,
                    next_chore_month,
                    WEEKDAYS.index(self._chore_day),
                ),
                next_chore_month.month,
            )
        return (
            MonthlyChore.nth_weekday_date(
                self._weekday_order_number,
                next_chore_month,
                WEEKDAYS.index(self._chore_day),
            ),
            next_chore_month.month,
        )

    def _add_period_offset(self, start_date: date) -> date:
        return start_date + relativedelta(months=self._period)

    def _find_candidate_date(self, day1: date) -> date | None:
        schedule_start_date = self._calculate_schedule_start_date()
        day1 = self.calculate_day1(day1, schedule_start_date)
        if self.last_completed is not None and self.last_completed.month == day1.month:
            if day1.month == 12:
                day1 = date(day1.year + 1, 1, 1)
            else:
                day1 = date(day1.year, day1.month + 1, 1)
        if self._period is None or self._period == 1:
            return self._monthly_candidate(day1, schedule_start_date)[0]
        result = self._monthly_candidate(day1, schedule_start_date)

        candidate_date = result[0]
        candidate_month = result[1]
        while (candidate_month - schedule_start_date.month) % self._period != 0:
            remainder = (
                candidate_date.month - schedule_start_date.month
            ) % self._period
            result = self._monthly_candidate(
                candidate_date + relativedelta(months=remainder, day=1),
                schedule_start_date,
            )
            candidate_date = result[0]
            candidate_month = result[1]

        if self._due_date_offset is not None:
            candidate_date += timedelta(days=self._due_date_offset)

        return candidate_date
