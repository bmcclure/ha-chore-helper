"""Sensor platform for chore_helper."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any, Dict, Generator

from dateutil.relativedelta import relativedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_HIDDEN,
    CONF_NAME,
    WEEKDAYS,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo
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
        add_devices = _frequency_function[frequency]
        async_add_devices([add_devices(config_entry)], True)
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
        "_last_month",
        "_last_updated",
        "_manual",
        "_next_due_date",
        "_overdue",
        "_overdue_days",
        "_frequency",
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
        self._date_format = config.get(
            const.CONF_DATE_FORMAT, const.DEFAULT_DATE_FORMAT
        )
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

    async def async_added_to_hass(self) -> None:
        """When sensor is added to hassio, add it to calendar."""
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

        # Create device
        device_registry = dr.async_get(self.hass)
        device_registry.async_get_or_create(
            config_entry_id=self.config_entry.entry_id,
            identifiers={(const.DOMAIN, self.unique_id)},
            name=self._attr_name,
            manufacturer="bmcclure",
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
        """When sensor is added to hassio, remove it."""
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
    def device_info(self) -> DeviceInfo | None:
        """Return device info."""
        return {
            "identifiers": {(const.DOMAIN, self.unique_id)},
            "name": self.config_entry.data.get("name"),
            "manufacturer": "bmcclure",
        }

    @property
    def name(self) -> str | None:
        """Return the name of the sensor."""
        return self._attr_name

    @property
    def next_due_date(self) -> date | None:
        """Return next date attribute."""
        return self._next_due_date

    @property
    def hidden(self) -> bool:
        """Return the hidden attribute."""
        return self._hidden

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return unit of measurement - None for numerical value."""
        return None

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
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return the state attributes."""
        state_attr = {
            const.ATTR_DAYS: self._days,
            const.ATTR_LAST_COMPLETED: self.last_completed,
            const.ATTR_LAST_UPDATED: self._last_updated,
            const.ATTR_NEXT_DATE: None
            if self._next_due_date is None
            else datetime(
                self._next_due_date.year,
                self._next_due_date.month,
                self._next_due_date.day,
            ).astimezone(),
            # Needed for translations to work
            ATTR_DEVICE_CLASS: self.DEVICE_CLASS,
        }
        return state_attr

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
                (
                    isinstance(self.last_completed, datetime)
                    and self.last_completed.date() == today
                )
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

    def chore_schedule(
        self, date1: date | None = None, date2: date | None = None
    ) -> Generator[date, None, None]:
        """Get dates within configured date range."""
        today = helpers.now().date()
        first_date: date = date(today.year - 1, 1, 1) if date1 is None else date1
        last_date: date = date(today.year + 1, 12, 31) if date2 is None else date2
        first_date = self.move_to_range(first_date)
        while True:
            try:
                next_due_date = self._find_candidate_date(first_date)
            except (TypeError, ValueError):
                return
            if next_due_date is None or next_due_date > last_date:
                return
            if (new_date := self.move_to_range(next_due_date)) != next_due_date:
                first_date = new_date  # continue from next year
            else:
                yield next_due_date
                first_date = next_due_date + relativedelta(
                    days=1
                )  # look from the next day

    async def _async_load_due_dates(self) -> None:
        """Fill the chore dates list."""
        self._due_dates.clear()
        for chore_date in self.chore_schedule():
            self._due_dates.append(chore_date)
        # self._due_dates.sort()

    async def add_date(self, chore_date: date) -> None:
        """Add date to _due_dates."""
        if chore_date not in self._due_dates:
            self._due_dates.append(chore_date)
            self._due_dates.sort()
        else:
            LOGGER.warning(
                "%s not added to %s - already on the chore schedule",
                chore_date,
                self.name,
            )

    async def remove_date(self, chore_date: date) -> None:
        """Remove date from _chore dates."""
        try:
            self._due_dates.remove(chore_date)
        except ValueError:
            LOGGER.warning(
                "%s not removed from %s - not in the chore schedule",
                chore_date,
                self.name,
            )

    def get_next_due_date(self, first_date: date, ignore_today=False) -> date | None:
        """Get next date from self._due_dates."""
        current_date_time = helpers.now()
        for d in self._due_dates:  # pylint: disable=invalid-name
            if d < first_date:
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
        self._next_due_date = self.get_next_due_date(today)
        if self._next_due_date is not None:
            LOGGER.debug(
                "(%s) next_due_date (%s), today (%s)",
                self._attr_name,
                self._next_due_date,
                today,
            )
            self._days = (self._next_due_date - today).days
            next_due_date_txt = self._next_due_date.strftime(self._date_format)
            LOGGER.debug(
                "(%s) Found next chore date: %s, that is in %d days",
                self._attr_name,
                next_due_date_txt,
                self._days,
            )
            if self._days > 1:
                self._attr_state = 2
                self._attr_icon = self._icon_normal
            else:
                if self._days == 0:
                    self._attr_state = self._days
                    self._attr_icon = self._icon_today
                elif self._days == 1:
                    self._attr_state = self._days
                    self._attr_icon = self._icon_tomorrow
        else:
            self._days = None
            self._attr_state = None
            self._attr_icon = self._icon_normal


class WeeklyChore(Chore):
    """Chore every n weeks, odd weeks or even weeks."""

    __slots__ = "_chore_days", "_first_week", "_period"

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Read parameters specific for Weekly Chore Frequency."""
        super().__init__(config_entry)
        config = config_entry.options
        self._chore_days = config.get(const.CONF_CHORE_DAYS, [])
        self._period: int
        self._first_week: int
        frequency = config.get(const.CONF_FREQUENCY)
        self._period = config.get(const.CONF_PERIOD, 1)
        self._first_week = config.get(const.CONF_FIRST_WEEK, 1)

    def _find_candidate_date(self, day1: date) -> date | None:
        """Calculate possible date, for weekly frequency."""
        week = day1.isocalendar()[1]
        weekday = day1.weekday()
        offset = -1
        if (week - self._first_week) % self._period == 0:  # Chore this week
            for day_name in self._chore_days:
                day_index = WEEKDAYS.index(day_name)
                if day_index >= weekday:  # Chore still did not happen
                    offset = day_index - weekday
                    break
        iterate_by_week = 7 - weekday + WEEKDAYS.index(self._chore_days[0])
        while offset == -1:  # look in following weeks
            candidate = day1 + relativedelta(days=iterate_by_week)
            week = candidate.isocalendar()[1]
            if (week - self._first_week) % self._period == 0:
                offset = iterate_by_week
                break
            iterate_by_week += 7
        return day1 + relativedelta(days=offset)


class DailyChore(Chore):
    """Chore every n days."""

    __slots__ = "_first_date", "_period"

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Read parameters specific for Daily Chore Frequency."""
        super().__init__(config_entry)
        config = config_entry.options
        self._period = config.get(const.CONF_PERIOD)
        self._first_date: date | None
        try:
            self._first_date = helpers.to_date(config.get(const.CONF_FIRST_DATE))
        except ValueError:
            self._first_date = None

    def _find_candidate_date(self, day1: date) -> date | None:
        """Calculate possible date, for every-n-days frequency."""
        try:
            if (day1 - self._first_date).days % self._period == 0:  # type: ignore
                return day1
            offset = self._period - (
                (day1 - self._first_date).days % self._period  # type: ignore
            )
        except TypeError as error:
            raise ValueError(
                f"({self._attr_name}) Please configure first_date and period "
                "for every-n-days chore frequency."
            ) from error
        return day1 + relativedelta(days=offset)


class MonthlyChore(Chore):
    """Chore every nth weekday of each month."""

    __slots__ = (
        "_chore_days",
        "_monthly_force_week_numbers",
        "_period",
        "_weekday_order_numbers",
        "_week_order_numbers",
    )

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Read parameters specific for Monthly Chore Frequency."""
        super().__init__(config_entry)
        config = config_entry.options
        self._chore_days = config.get(const.CONF_CHORE_DAYS, [])
        self._monthly_force_week_numbers = config.get(
            const.CONF_FORCE_WEEK_NUMBERS, False
        )
        self._weekday_order_numbers: list
        self._week_order_numbers: list
        order_numbers: list = []
        if const.CONF_WEEKDAY_ORDER_NUMBER in config:
            order_numbers = list(map(int, config[const.CONF_WEEKDAY_ORDER_NUMBER]))
        if self._monthly_force_week_numbers:
            self._weekday_order_numbers = []
            self._week_order_numbers = order_numbers
        else:
            self._weekday_order_numbers = order_numbers
            self._week_order_numbers = []
        self._period = config.get(const.CONF_PERIOD, 1)

    @staticmethod
    def nth_week_date(week_number: int, date_of_month: date, chore_day: int) -> date:
        """Find weekday in the nth week of the month."""
        first_of_month = date(date_of_month.year, date_of_month.month, 1)
        return first_of_month + relativedelta(
            days=chore_day - first_of_month.weekday() + (week_number - 1) * 7
        )

    @staticmethod
    def nth_weekday_date(
        weekday_number: int, date_of_month: date, chore_day: int
    ) -> date:
        """Find nth weekday of the month."""
        first_of_month = date(date_of_month.year, date_of_month.month, 1)
        # 1st of the month is before the day of chore
        # (so 1st chore week the week when month starts)
        if chore_day >= first_of_month.weekday():
            return first_of_month + relativedelta(
                days=chore_day - first_of_month.weekday() + (weekday_number - 1) * 7
            )
        return first_of_month + relativedelta(
            days=7 - first_of_month.weekday() + chore_day + (weekday_number - 1) * 7
        )

    def _monthly_candidate(self, day1: date) -> date:
        """Calculate possible date, for monthly frequency."""
        if self._monthly_force_week_numbers:
            for week_order_number in self._week_order_numbers:
                candidate_date = MonthlyChore.nth_week_date(
                    week_order_number, day1, WEEKDAYS.index(self._chore_days[0])
                )
                # date is today or in the future -> we have the date
                if candidate_date >= day1:
                    return candidate_date
        else:
            for weekday_order_number in self._weekday_order_numbers:
                candidate_date = MonthlyChore.nth_weekday_date(
                    weekday_order_number,
                    day1,
                    WEEKDAYS.index(self._chore_days[0]),
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
                self._week_order_numbers[0],
                next_chore_month,
                WEEKDAYS.index(self._chore_days[0]),
            )
        return MonthlyChore.nth_weekday_date(
            self._weekday_order_numbers[0],
            next_chore_month,
            WEEKDAYS.index(self._chore_days[0]),
        )

    def _find_candidate_date(self, day1: date) -> date | None:
        if self._period is None or self._period == 1:
            return self._monthly_candidate(day1)
        else:
            candidate_date = self._monthly_candidate(day1)
            while (candidate_date.month - self._first_month) % self._period != 0:
                candidate_date = self._monthly_candidate(
                    candidate_date + relativedelta(days=1)
                )
            return candidate_date


class YearlyChore(Chore):
    """Chore every year."""

    __slots__ = ("_date",)

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Read parameters specific for Yearly Chore Frequency."""
        super().__init__(config_entry)
        config = config_entry.options
        self._date = config.get(const.CONF_DATE)

    def _find_candidate_date(self, day1: date) -> date | None:
        """Calculate possible date, for yearly frequency."""
        year = day1.year
        try:
            conf_date = datetime.strptime(self._date, "%m/%d").date()
        except TypeError as error:
            raise ValueError(
                f"({self._attr_name}) Please configure the date "
                "for yearly chore frequency."
            ) from error
        if (candidate_date := date(year, conf_date.month, conf_date.day)) < day1:
            candidate_date = date(year + 1, conf_date.month, conf_date.day)
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
