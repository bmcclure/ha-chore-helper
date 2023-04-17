"""Sensor platform for chore_helper."""
from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, time, timedelta
from typing import Any
from collections.abc import Generator

from dateutil.relativedelta import relativedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    ATTR_HIDDEN,
    CONF_NAME,
    WEEKDAYS,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import const, helpers
from .const import LOGGER
from .calendar import EntitiesCalendarData


SCAN_INTERVAL = timedelta(seconds=10)
THROTTLE_INTERVAL = timedelta(seconds=60)


async def async_setup_entry(
    _: HomeAssistant, config_entry: ConfigEntry, async_add_devices: AddEntitiesCallback
) -> None:
    """Create chore entities defined in config_flow and add them to HA."""
    frequency = config_entry.options.get(const.CONF_FREQUENCY)
    name = (
        config_entry.title
        if config_entry.title is not None
        else config_entry.data.get(CONF_NAME)
    )
    _frequency_function = {
        "every-n-days": DailyChore,
        "every-n-weeks": WeeklyChore,
        "every-n-months": MonthlyChore,
        "every-n-years": YearlyChore,
        "after-n-days": DailyChore,
        "after-n-weeks": WeeklyChore,
        "after-n-months": MonthlyChore,
        "after-n-years": YearlyChore,
        "blank": BlankChore,
    }
    if frequency in _frequency_function:
        async_add_devices([_frequency_function[frequency](config_entry)], True)
    else:
        LOGGER.error("(%s) Unknown frequency %s", name, frequency)
        raise ValueError


class Chore(RestoreEntity):
    """Chore Sensor class."""

    __slots__ = (
        "_attr_icon",
        "_attr_name",
        "_attr_state",
        "_due_dates",
        "_date_format",
        "_days",
        "_first_month",
        "_hidden",
        "_icon_normal",
        "_icon_today",
        "_icon_tomorrow",
        "_icon_overdue",
        "_last_month",
        "_last_updated",
        "_manual",
        "_next_due_date",
        "_forecast_dates",
        "_overdue",
        "_overdue_days",
        "_frequency",
        "_start_date",
        "_offset_dates",
        "_add_dates",
        "_remove_dates",
        "config_entry",
        "last_completed",
    )

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Read configuration and initialise class variables."""
        config = config_entry.options
        self.config_entry = config_entry
        self._attr_name = (
            config_entry.title
            if config_entry.title is not None
            else config.get(CONF_NAME)
        )
        self._hidden = config.get(ATTR_HIDDEN, False)
        self._manual = config.get(const.CONF_MANUAL)
        first_month = config.get(const.CONF_FIRST_MONTH, const.DEFAULT_FIRST_MONTH)
        months = [m["value"] for m in const.MONTH_OPTIONS]
        self._first_month: int = (
            months.index(first_month) + 1 if first_month in months else 1
        )
        last_month = config.get(const.CONF_LAST_MONTH, const.DEFAULT_LAST_MONTH)
        self._last_month: int = (
            months.index(last_month) + 1 if last_month in months else 12
        )
        self._icon_normal = config.get(const.CONF_ICON_NORMAL)
        self._icon_today = config.get(const.CONF_ICON_TODAY)
        self._icon_tomorrow = config.get(const.CONF_ICON_TOMORROW)
        self._icon_overdue = config.get(const.CONF_ICON_OVERDUE)
        self._date_format = config.get(
            const.CONF_DATE_FORMAT, const.DEFAULT_DATE_FORMAT
        )
        self._forecast_dates: int = config.get(const.CONF_FORECAST_DATES) or 0
        self._due_dates: list[date] = []
        self._next_due_date: date | None = None
        self._last_updated: datetime | None = None
        self.last_completed: datetime | None = None
        self._days: int | None = None
        self._overdue: bool = False
        self._overdue_days: int | None = None
        self._frequency: str = config.get(const.CONF_FREQUENCY)
        self._attr_state = self._days
        self._attr_icon = self._icon_normal
        self._start_date: date | None
        self._offset_dates: str = None
        self._add_dates: str = None
        self._remove_dates: str = None
        try:
            self._start_date = helpers.to_date(config.get(const.CONF_START_DATE))
        except ValueError:
            self._start_date = None

    async def async_added_to_hass(self) -> None:
        """When sensor is added to HA, restore state and add it to calendar."""
        await super().async_added_to_hass()
        self.hass.data[const.DOMAIN][const.SENSOR_PLATFORM][self.entity_id] = self

        # Restore stored state
        if (state := await self.async_get_last_state()) is not None:
            self._last_updated = None  # Unblock update - after options change
            self._attr_state = state.state
            self._days = (
                state.attributes[const.ATTR_DAYS]
                if const.ATTR_DAYS in state.attributes
                else None
            )
            next_due_date = (
                helpers.parse_datetime(state.attributes[const.ATTR_NEXT_DATE])
                if const.ATTR_NEXT_DATE in state.attributes
                else None
            )
            self._next_due_date = (
                None if next_due_date is None else next_due_date.date()
            )
            self.last_completed = (
                helpers.parse_datetime(state.attributes[const.ATTR_LAST_COMPLETED])
                if const.ATTR_LAST_COMPLETED in state.attributes
                else None
            )
            self._overdue = (
                state.attributes[const.ATTR_OVERDUE]
                if const.ATTR_OVERDUE in state.attributes
                else False
            )
            self._overdue_days = (
                state.attributes[const.ATTR_OVERDUE_DAYS]
                if const.ATTR_OVERDUE_DAYS in state.attributes
                else None
            )
            self._offset_dates = (
                state.attributes[const.ATTR_OFFSET_DATES]
                if const.ATTR_OFFSET_DATES in state.attributes
                else None
            )
            self._add_dates = (
                state.attributes[const.ATTR_ADD_DATES]
                if const.ATTR_ADD_DATES in state.attributes
                else None
            )
            self._remove_dates = (
                state.attributes[const.ATTR_REMOVE_DATES]
                if const.ATTR_REMOVE_DATES in state.attributes
                else None
            )

        # Create or add to calendar
        if not self.hidden:
            if const.CALENDAR_PLATFORM not in self.hass.data[const.DOMAIN]:
                self.hass.data[const.DOMAIN][
                    const.CALENDAR_PLATFORM
                ] = EntitiesCalendarData(self.hass)
                LOGGER.debug("Creating chore calendar")
                await self.hass.config_entries.async_forward_entry_setup(
                    self.config_entry, const.CALENDAR_PLATFORM
                )

            self.hass.data[const.DOMAIN][const.CALENDAR_PLATFORM].add_entity(
                self.entity_id
            )

    async def async_will_remove_from_hass(self) -> None:
        """When sensor is removed from HA, remove it and its calendar entity."""
        await super().async_will_remove_from_hass()
        del self.hass.data[const.DOMAIN][const.SENSOR_PLATFORM][self.entity_id]
        self.hass.data[const.DOMAIN][const.CALENDAR_PLATFORM].remove_entity(
            self.entity_id
        )

    @property
    def unique_id(self) -> str:
        """Return a unique ID to use for this sensor."""
        if "unique_id" in self.config_entry.data:  # From legacy config
            return self.config_entry.data["unique_id"]
        return self.config_entry.entry_id

    @property
    def name(self) -> str | None:
        """Return the name of the sensor."""
        return self._attr_name

    @property
    def next_due_date(self) -> date | None:
        """Return next date attribute."""
        return self._next_due_date

    @property
    def overdue(self) -> bool:
        """Return overdue attribute."""
        return self._overdue

    @property
    def overdue_days(self) -> int | None:
        """Return overdue_days attribute."""
        return self._overdue_days

    @property
    def offset_dates(self) -> str:
        """Return offset_dates attribute."""
        return self._offset_dates

    @property
    def add_dates(self) -> str:
        """Return add_dates attribute."""
        return self._add_dates

    @property
    def remove_dates(self) -> str:
        """Return remove_dates attribute."""
        return self._remove_dates

    @property
    def hidden(self) -> bool:
        """Return the hidden attribute."""
        return self._hidden

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return unit of measurement - None for numerical value."""
        return "day" if self._days == 1 else "days"

    @property
    def native_value(self) -> object:
        """Return the state of the sensor."""
        return self._attr_state

    @property
    def last_updated(self) -> datetime | None:
        """Return when the sensor was last updated."""
        return self._last_updated

    @property
    def icon(self) -> str:
        """Return the entity icon."""
        return self._attr_icon

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {
            const.ATTR_LAST_COMPLETED: self.last_completed,
            const.ATTR_LAST_UPDATED: self.last_updated,
            const.ATTR_OVERDUE: self.overdue,
            const.ATTR_OVERDUE_DAYS: self.overdue_days,
            const.ATTR_NEXT_DATE: self.next_due_date,
            const.ATTR_OFFSET_DATES: self.offset_dates,
            const.ATTR_ADD_DATES: self.add_dates,
            const.ATTR_REMOVE_DATES: self.remove_dates,
            ATTR_UNIT_OF_MEASUREMENT: self.native_unit_of_measurement,
            # Needed for translations to work
            ATTR_DEVICE_CLASS: self.DEVICE_CLASS,
        }

    @property
    def DEVICE_CLASS(self) -> str:  # pylint: disable=C0103
        """Return the class of the sensor."""
        return const.DEVICE_CLASS

    def __repr__(self) -> str:
        """Return main sensor parameters."""
        return (
            f"{self.__class__.__name__}(name={self._attr_name}, "
            f"entity_id={self.entity_id}, "
            f"state={self.state}, "
            f"attributes={self.extra_state_attributes})"
        )

    def _find_candidate_date(self, day1: date) -> date | None:
        """Find the next possible date starting from day1.

        Only based on calendar, not looking at include/exclude days.
        Must be implemented for each child class.
        """
        raise NotImplementedError

    async def _async_ready_for_update(self) -> bool:
        """Check if the entity is ready for the update.

        Skip the update if the sensor was updated today
        Except for the sensors with with next date today and after the expiration time
        """
        current_date_time = helpers.now()
        today = current_date_time.date()
        try:
            ready_for_update = bool(self._last_updated.date() != today)  # type: ignore
        except AttributeError:
            return True
        try:
            if self._next_due_date == today and (
                isinstance(self.last_completed, datetime)
                and self.last_completed.date() == today
            ):
                return True
        except (AttributeError, TypeError):
            pass
        return ready_for_update

    def date_inside(self, dat: date) -> bool:
        """Check if the date is inside first and last date."""
        month = dat.month
        if self._first_month <= self._last_month:
            return bool(self._first_month <= month <= self._last_month)
        return bool(self._first_month <= month or month <= self._last_month)

    def move_to_range(self, day: date) -> date:
        """If the date is not in range, move to the range."""
        if not self.date_inside(day):
            year = day.year
            month = day.month
            months = [m["label"] for m in const.MONTH_OPTIONS]
            if self._first_month <= self._last_month < month:
                LOGGER.debug(
                    "(%s) %s outside the range, looking from %s next year",
                    self._attr_name,
                    day,
                    months[self._first_month - 1],
                )
                return date(year + 1, self._first_month, 1)
            LOGGER.debug(
                "(%s) %s outside the range, searching from %s",
                self._attr_name,
                day,
                months[self._first_month - 1],
            )
            return date(year, self._first_month, 1)
        return day

    def _calculate_start_date(self) -> date:
        """Calculate start date based on the last completed date."""
        start_date = (
            self._start_date
            if self._start_date is not None
            else date(helpers.now().date().year - 1, 1, 1)
        )
        if self.last_completed is not None:
            last_completed = self.last_completed.date()
            if last_completed > start_date:
                start_date = last_completed
            elif last_completed == start_date:
                start_date += timedelta(days=1)
        return self.move_to_range(start_date)

    def _calculate_schedule_start_date(self) -> date:
        """Calculate start date for scheduling offsets."""
        after = self._frequency[:6] == "after-"
        start_date = self._start_date
        if after and self.last_completed is not None:
            last_completed = self.last_completed.date()
            if last_completed > start_date:
                start_date = last_completed
        return start_date

    def chore_schedule(self) -> Generator[date, None, None]:
        """Get dates within configured date range."""
        start_date: date = self._calculate_start_date()
        for _ in range(int(self._forecast_dates) + 1):
            try:
                next_due_date = self._find_candidate_date(start_date)
            except (TypeError, ValueError):
                break
            if next_due_date is None:
                break
            if (new_date := self.move_to_range(next_due_date)) != next_due_date:
                start_date = new_date
            else:
                should_remove = False
                if self._remove_dates is not None:
                    for remove_date in self._remove_dates.split(" "):
                        if remove_date == (next_due_date.strftime("%Y-%m-%d")):
                            should_remove = True
                            break
                if not should_remove:
                    offset = None
                    if self._offset_dates is not None:
                        offset_compare = next_due_date.strftime("%Y-%m-%d")
                        for offset_date in self._offset_dates.split(" "):
                            if offset_date.startswith(offset_compare):
                                offset = int(offset_date.split(":")[1])
                                break
                    yield next_due_date if offset is None else next_due_date + relativedelta(
                        days=offset
                    )
                start_date = next_due_date + relativedelta(
                    days=1
                )  # look from the next day
        if self._add_dates is not None:
            for add_date_str in self._add_dates.split(" "):
                yield datetime.strptime(add_date_str, "%Y-%m-%d").date()
        return

    async def _async_load_due_dates(self) -> None:
        """Fill the chore dates list."""
        self._due_dates.clear()
        for chore_date in self.chore_schedule():
            self._due_dates.append(chore_date)
        self._due_dates.sort()

    async def add_date(self, chore_date: date) -> None:
        """Add date to due dates."""
        add_dates = self._add_dates.split(" ") if self._add_dates else []
        date_str = chore_date.strftime("%Y-%m-%d")
        if date_str not in add_dates:
            add_dates.append(date_str)
            add_dates.sort()
            self._add_dates = " ".join(add_dates)
        else:
            LOGGER.warning(
                "%s was already added to %s",
                chore_date,
                self.name,
            )
        self.update_state()

    async def remove_date(self, chore_date: date | None = None) -> None:
        """Remove date from chore dates."""
        if chore_date is None:
            chore_date = self.next_due_date
        if chore_date is None:
            LOGGER.warning("No date to remove from %s", self.name)
            return
        remove_dates = self._remove_dates.split(" ") if self._remove_dates else []
        date_str = chore_date.strftime("%Y-%m-%d")
        if date_str not in remove_dates:
            remove_dates.append(date_str)
            remove_dates.sort()
            self._remove_dates = " ".join(remove_dates)
        else:
            LOGGER.warning(
                "%s was already removed from %s",
                chore_date,
                self.name,
            )
        self.update_state()

    async def offset_date(self, offset: int, chore_date: date | None = None) -> None:
        """Offset date in chore dates."""
        if chore_date is None:
            chore_date = self.next_due_date
        if chore_date is None:
            LOGGER.warning("No date to offset from %s", self.name)
            return
        offset_dates = (
            [
                x
                for x in self._offset_dates.split(" ")
                if not x.startswith(chore_date.strftime("%Y-%m-%d"))
            ]
            if self._offset_dates is not None
            else []
        )
        date_str = chore_date.strftime("%Y-%m-%d")
        offset_dates.append(f"{date_str}:{offset}")
        offset_dates.sort()
        self._offset_dates = " ".join(offset_dates)
        self.update_state()

    def get_next_due_date(self, start_date: date, ignore_today=False) -> date | None:
        """Get next date from self._due_dates."""
        current_date_time = helpers.now()
        for d in self._due_dates:  # pylint: disable=invalid-name
            if d < start_date:
                continue
            if not ignore_today and d == current_date_time.date():
                expiration = time(23, 59, 59)

                if current_date_time.time() > expiration or (
                    self.last_completed is not None
                    and self.last_completed.date() == current_date_time.date()
                    and current_date_time.time() >= self.last_completed.time()
                ):
                    continue
            return d
        return None

    async def async_update(self) -> None:
        """Get the latest data and updates the states."""
        if not await self._async_ready_for_update() or not self.hass.is_running:
            return

        LOGGER.debug("(%s) Calling update", self._attr_name)
        await self._async_load_due_dates()
        LOGGER.debug(
            "(%s) Dates loaded, firing a chore_helper_loaded event",
            self._attr_name,
        )
        event_data = {
            "entity_id": self.entity_id,
            "due_dates": helpers.dates_to_texts(self._due_dates),
        }
        self.hass.bus.async_fire("chore_helper_loaded", event_data)
        if not self._manual:
            self.update_state()

    def update_state(self) -> None:
        """Pick the first event from chore dates, update attributes."""
        LOGGER.debug("(%s) Looking for next chore date", self._attr_name)
        self._last_updated = helpers.now()
        today = self._last_updated.date()
        self._next_due_date = self.get_next_due_date(self._calculate_start_date())
        if self._next_due_date is not None:
            LOGGER.debug(
                "(%s) next_due_date (%s), today (%s)",
                self._attr_name,
                self._next_due_date,
                today,
            )
            self._days = (self._next_due_date - today).days
            LOGGER.debug(
                "(%s) Found next chore date: %s, that is in %d days",
                self._attr_name,
                self._next_due_date,
                self._days,
            )
            self._attr_state = self._days
            if self._days > 1:
                self._attr_icon = self._icon_normal
            elif self._days < 0:
                self._attr_icon = self._icon_overdue
            elif self._days == 0:
                self._attr_icon = self._icon_today
            elif self._days == 1:
                self._attr_icon = self._icon_tomorrow
            self._overdue = self._days < 0
            self._overdue_days = 0 if self._days > -1 else abs(self._days)
        else:
            self._days = None
            self._attr_state = None
            self._attr_icon = self._icon_normal
            self._overdue = False
            self._overdue_days = None

        start_date = self._calculate_start_date()
        if self._add_dates is not None:
            self._add_dates = " ".join(
                [
                    x
                    for x in self._add_dates.split(" ")
                    if datetime.strptime(x, "%Y-%m-%d").date() >= start_date
                ]
            )
        if self._remove_dates is not None:
            self._remove_dates = " ".join(
                [
                    x
                    for x in self._remove_dates.split(" ")
                    if datetime.strptime(x, "%Y-%m-%d").date() >= start_date
                ]
            )
        if self._offset_dates is not None:
            self._offset_dates = " ".join(
                [
                    x
                    for x in self._offset_dates.split(" ")
                    if datetime.strptime(x.split(":")[0], "%Y-%m-%d").date()
                    >= start_date
                ]
            )

    def calculate_day1(self, day1: date, schedule_start_date: date) -> date:
        """Calculate day1."""
        start_date = self._calculate_start_date()
        if start_date > day1:
            day1 = start_date
        if schedule_start_date > day1:
            day1 = schedule_start_date
        today = helpers.now().date()
        if (
            day1 == today
            and self.last_completed is not None
            and self.last_completed.date() == today
        ):
            day1 = day1 + relativedelta(days=1)
        return day1


class DailyChore(Chore):
    """Chore every n days."""

    __slots__ = ("_period",)

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Read parameters specific for Daily Chore Frequency."""
        super().__init__(config_entry)
        config = config_entry.options
        self._period = config.get(const.CONF_PERIOD)

    def _find_candidate_date(self, day1: date) -> date | None:
        """Calculate possible date, for every-n-days frequency."""
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

    def _find_candidate_date(self, day1: date) -> date | None:
        """Calculate possible date, for weekly frequency."""
        start_date = self._calculate_schedule_start_date()
        start_week = start_date.isocalendar()[1]
        day1 = self.calculate_day1(day1, start_date)
        week = day1.isocalendar()[1]
        weekday = day1.weekday()
        offset = -1
        if (week - start_week) % self._period == 0:  # Chore this week
            if self._chore_day is not None:
                day_index = WEEKDAYS.index(self._chore_day)
                if day_index >= weekday:  # Chore still did not happen
                    offset = day_index - weekday
        iterate_by_week = 7 - weekday + WEEKDAYS.index(self._chore_day)
        while offset == -1:  # look in following weeks
            candidate = day1 + relativedelta(days=iterate_by_week)
            week = candidate.isocalendar()[1]
            if (week - start_week) % self._period == 0:
                offset = iterate_by_week
                break
            iterate_by_week += 7
        return day1 + relativedelta(days=offset)


class MonthlyChore(Chore):
    """Chore every nth weekday of each month."""

    __slots__ = (
        "_day_of_month",
        "_chore_day",
        "_monthly_force_week_numbers",
        "_period",
        "_weekday_order_number",
        "_week_order_number",
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
    def viable_weeks_in_month(date_of_month: date, chore_day: int):
        """Find the highest week number that contains the chore day in the month."""
        first_of_month = date(date_of_month.year, date_of_month.month, 1)
        last_of_month = first_of_month + relativedelta(day=31)
        first_week = first_of_month.isocalendar()[1]
        last_chore_day_offset = (last_of_month.weekday() - chore_day) % 7
        last_chore_day = last_of_month - timedelta(days=last_chore_day_offset)
        last_chore_week = last_chore_day.isocalendar()[1]
        return last_chore_week - first_week + 1

    @staticmethod
    def nth_week_date(week_number: int, date_of_month: date, chore_day: int) -> date:
        """Find weekday in the nth week of the month."""
        first_of_month = date(date_of_month.year, date_of_month.month, 1)
        actual_week_number = (
            week_number
            if week_number > 0
            else max(
                MonthlyChore.viable_weeks_in_month(date_of_month, chore_day) + week_number + 1,
                1
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
                MonthlyChore.viable_weeks_in_month(date_of_month, chore_day) + weekday_number + 1,
                1
            )
        )

        # 1st of the month is before the day of chore
        # (so 1st chore week the week when month starts)
        if chore_day >= first_of_month.weekday():
            return first_of_month + relativedelta(
                days=chore_day - first_of_month.weekday() + (actual_weekday_number - 1) * 7
            )
        return first_of_month + relativedelta(
            days=7 - first_of_month.weekday() + chore_day + (actual_weekday_number - 1) * 7
        )

    def _monthly_candidate(self, day1: date, start_date: date) -> date:
        """Calculate possible date, for monthly frequency."""
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
                return date(day1.year, day1.month, day_of_month)
            if day1.month == 12:
                return date(day1.year + 1, 1, day_of_month)
            return date(day1.year, day1.month + 1, day_of_month)
        if self._monthly_force_week_numbers:
            if self._week_order_number is not None:
                candidate_date = MonthlyChore.nth_week_date(
                    self._week_order_number, day1, WEEKDAYS.index(self._chore_day)
                )
                # date is today or in the future -> we have the date
                if candidate_date >= day1:
                    return candidate_date
        else:
            if self._weekday_order_number is not None:
                candidate_date = MonthlyChore.nth_weekday_date(
                    self._weekday_order_number,
                    day1,
                    WEEKDAYS.index(self._chore_day),
                )
                # date is today or in the future -> we have the date
                if candidate_date >= day1:
                    return candidate_date
        if day1.month == 12:
            next_chore_month = date(day1.year + 1, 1, 1)
        else:
            next_chore_month = date(day1.year, day1.month + 1, 1)
        if self._monthly_force_week_numbers:
            return MonthlyChore.nth_week_date(
                self._week_order_number,
                next_chore_month,
                WEEKDAYS.index(self._chore_day),
            )
        return MonthlyChore.nth_weekday_date(
            self._weekday_order_number,
            next_chore_month,
            WEEKDAYS.index(self._chore_day),
        )

    def _find_candidate_date(self, day1: date) -> date | None:
        schedule_start_date = self._calculate_schedule_start_date()
        day1 = self.calculate_day1(day1, schedule_start_date)
        if self.last_completed is not None and self.last_completed.month == day1.month:
            if day1.month == 12:
                day1 = date(day1.year + 1, 1, 1)
            else:
                day1 = date(day1.year, day1.month + 1, 1)
        if self._period is None or self._period == 1:
            return self._monthly_candidate(day1, schedule_start_date)
        candidate_date = self._monthly_candidate(day1, schedule_start_date)
        while (candidate_date.month - schedule_start_date.month) % self._period != 0:
            candidate_date = self._monthly_candidate(
                candidate_date + relativedelta(days=1), schedule_start_date
            )
        return candidate_date


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


class BlankChore(Chore):
    """No chore due date - for manual update."""

    def _find_candidate_date(self, day1: date) -> date | None:
        """Do not return any date for blank frequency."""
        return None

    async def _async_load_due_dates(self) -> None:
        """Clear chore dates (filled in by the blueprint)."""
        self._due_dates.clear()
        return

    async def async_update(self) -> None:
        """Get the latest data and updates the states."""
        if not await self._async_ready_for_update() or not self.hass.is_running:
            return
        LOGGER.debug("(%s) Calling update", self._attr_name)
        await self._async_load_due_dates()
        LOGGER.debug(
            "(%s) Dates loaded, firing a chore_helper_loaded event",
            self._attr_name,
        )
        event_data = {
            "entity_id": self.entity_id,
            "due_dates": [],
        }
        self.hass.bus.async_fire("chore_helper_loaded", event_data)
