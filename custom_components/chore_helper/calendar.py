"""Chore Helper calendar."""

from __future__ import annotations
import contextlib

from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import Throttle

from .const import CALENDAR_NAME, CALENDAR_PLATFORM, DOMAIN, SENSOR_PLATFORM

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=1)


# pylint: disable=unused-argument
async def async_setup_entry(
    _: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add calendar entity to HA."""
    async_add_entities([ChoreCalendar()], True)


class ChoreCalendar(CalendarEntity):
    """The chore helper calendar class."""

    instances = False

    def __init__(self) -> None:
        """Create empty calendar."""
        self._cal_data: dict = {}
        self._attr_name = CALENDAR_NAME
        ChoreCalendar.instances = True

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        return self.hass.data[DOMAIN][CALENDAR_PLATFORM].event

    @property
    def name(self) -> str | None:
        """Return the name of the entity."""
        return self._attr_name

    async def async_update(self) -> None:
        """Update all calendars."""
        await self.hass.data[DOMAIN][CALENDAR_PLATFORM].async_update()

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Get all events in a specific time frame."""
        return await self.hass.data[DOMAIN][CALENDAR_PLATFORM].async_get_events(
            hass, start_date, end_date
        )

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return the device state attributes."""
        if self.hass.data[DOMAIN][CALENDAR_PLATFORM].event is None:
            # No tasks, we don't need to show anything.
            return None
        return {}


class EntitiesCalendarData:
    """Class used by the Entities Calendar class to hold all entity events."""

    __slots__ = "_hass", "event", "entities", "_throttle"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize an Entities Calendar Data."""
        self._hass = hass
        self.event: CalendarEvent | None = None
        self.entities: list[str] = []

    def add_entity(self, entity_id: str) -> None:
        """Append entity ID to the calendar."""
        if entity_id not in self.entities:
            self.entities.append(entity_id)

    def remove_entity(self, entity_id: str) -> None:
        """Remove entity ID from the calendar."""
        with contextlib.suppress(ValueError):
            self.entities.remove(entity_id)

    async def async_get_events(
        self, hass: HomeAssistant, start_datetime: datetime, end_datetime: datetime
    ) -> list[CalendarEvent]:
        """Get all tasks in a specific time frame."""
        events: list[CalendarEvent] = []
        if SENSOR_PLATFORM not in hass.data[DOMAIN]:
            return events
        start_date = start_datetime.date()
        end_date = end_datetime.date()
        for entity in self.entities:
            if (
                entity not in hass.data[DOMAIN][SENSOR_PLATFORM]
                or hass.data[DOMAIN][SENSOR_PLATFORM][entity].hidden
            ):
                continue
            chore = hass.data[DOMAIN][SENSOR_PLATFORM][entity]
            start = chore.get_next_due_date(start_date, True)
            today = datetime.now().date()
            while start is not None and start_date <= start <= end_date:
                if chore.show_overdue_today and (start < today):
                    start = today

                try:
                    end = start + timedelta(days=1)
                except TypeError:
                    end = start
                name = chore.name if chore.name is not None else "Unknown"
                event = CalendarEvent(
                    summary=name,
                    start=start,
                    end=end,
                )
                events.append(event)
                start = chore.get_next_due_date(start + timedelta(days=1), True)
        return events

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self) -> None:
        """Get the latest data."""
        next_due_dates = {}
        for entity in self.entities:
            if (
                self._hass.data[DOMAIN][SENSOR_PLATFORM][entity].next_due_date
                is not None
            ):
                next_due_dates[entity] = self._hass.data[DOMAIN][SENSOR_PLATFORM][
                    entity
                ].next_due_date
        if len(next_due_dates) > 0:
            entity_id = min(next_due_dates.keys(), key=lambda k: next_due_dates[k])
            start = next_due_dates[entity_id]
            end = start + timedelta(days=1)
            name = self._hass.data[DOMAIN][SENSOR_PLATFORM][entity_id].name
            self.event = CalendarEvent(
                summary=name,
                start=start,
                end=end,
            )
