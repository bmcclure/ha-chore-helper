"""Sensor platform for chore_helper."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import const
from .chore_blank import BlankChore
from .chore_daily import DailyChore
from .chore_monthly import MonthlyChore
from .chore_weekly import WeeklyChore
from .chore_yearly import YearlyChore
from .const import LOGGER


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
