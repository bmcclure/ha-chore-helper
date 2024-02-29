"""Custom integration to manage household chores with Home Assistant.

For more details about this integration, please refer to
https://github.com/bmcclure/ha-chore-helper
"""
from __future__ import annotations

from datetime import timedelta

import homeassistant.helpers.config_validation as cv
import homeassistant.util.dt as dt_util
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_HIDDEN,
    CONF_ENTITIES,
    CONF_ENTITY_ID,
    WEEKDAYS,
)
from homeassistant.core import HomeAssistant, ServiceCall
import voluptuous as vol

from . import const, helpers
from .const import LOGGER

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=30)

months = [m["value"] for m in const.MONTH_OPTIONS]
frequencies = [f["value"] for f in const.FREQUENCY_OPTIONS]

SENSOR_SCHEMA = vol.Schema(
    {
        vol.Required(const.CONF_FREQUENCY): vol.In(frequencies),
        vol.Required(const.CONF_ICON_NORMAL): cv.icon,
        vol.Optional(const.CONF_ICON_TODAY): cv.icon,
        vol.Optional(const.CONF_ICON_TOMORROW): cv.icon,
        vol.Optional(ATTR_HIDDEN): cv.boolean,
        vol.Optional(const.CONF_MANUAL): cv.boolean,
        vol.Optional(const.CONF_DATE): helpers.month_day_text,
        vol.Optional(const.CONF_TIME): cv.time,
        vol.Optional(CONF_ENTITIES): cv.entity_ids,
        vol.Optional(const.CONF_CHORE_DAY): vol.In(WEEKDAYS),
        vol.Optional(const.CONF_FIRST_MONTH): vol.In(months),
        vol.Optional(const.CONF_LAST_MONTH): vol.In(months),
        vol.Optional(const.CONF_WEEKDAY_ORDER_NUMBER): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=5)
        ),
        vol.Optional(const.CONF_PERIOD): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=1000)
        ),
        vol.Optional(const.CONF_FIRST_WEEK): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=52)
        ),
        vol.Optional(const.CONF_START_DATE): cv.date,
        vol.Optional(const.CONF_DATE_FORMAT): cv.string,
    },
    extra=vol.ALLOW_EXTRA,
)

CONFIG_SCHEMA = vol.Schema(
    {
        const.DOMAIN: vol.Schema(
            {vol.Optional(const.CONF_SENSORS): vol.All(cv.ensure_list, [SENSOR_SCHEMA])}
        )
    },
    extra=vol.ALLOW_EXTRA,
)

COMPLETE_NOW_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ENTITY_ID): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(const.ATTR_LAST_COMPLETED): cv.datetime,
    }
)

UPDATE_STATE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ENTITY_ID): vol.All(cv.ensure_list, [cv.string]),
    }
)

ADD_DATE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ENTITY_ID): vol.All(cv.ensure_list, [cv.string]),
        vol.Required(const.CONF_DATE): cv.date,
    }
)

REMOVE_DATE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ENTITY_ID): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(const.CONF_DATE): cv.date,
    }
)

ADD_REMOVE_TIME_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ENTITY_ID): vol.All(cv.ensure_list, [cv.string]),
        vol.Required(const.CONF_TIME): cv.time,
    }
)

OFFSET_DATE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ENTITY_ID): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(const.CONF_DATE): cv.date,
        vol.Required(const.CONF_OFFSET): vol.All(
            vol.Coerce(int), vol.Range(min=-31, max=31)
        ),
    }
)


# pylint: disable=unused-argument
async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up platform - register services, initialize data structure."""

    async def handle_add_date(call: ServiceCall) -> None:
        """Handle the add_date service call."""
        entity_ids = call.data.get(CONF_ENTITY_ID, [])
        chore_date = call.data.get(const.CONF_DATE)
        for entity_id in entity_ids:
            LOGGER.debug("called add_date %s from %s", chore_date, entity_id)
            try:
                entity = hass.data[const.DOMAIN][const.SENSOR_PLATFORM][entity_id]
                await entity.add_date(chore_date)
            except KeyError as err:
                LOGGER.error(
                    "Failed adding date %s to %s (%s)",
                    chore_date,
                    entity_id,
                    err,
                )

    async def handle_remove_date(call: ServiceCall) -> None:
        """Handle the remove_date service call."""
        entity_ids = call.data.get(CONF_ENTITY_ID, [])
        chore_date = call.data.get(const.CONF_DATE, None)
        for entity_id in entity_ids:
            LOGGER.debug("called remove_date %s from %s", chore_date, entity_id)
            try:
                entity = hass.data[const.DOMAIN][const.SENSOR_PLATFORM][entity_id]
                await entity.remove_date(chore_date)
            except KeyError as err:
                LOGGER.error(
                    "Failed removing date %s from %s (%s)",
                    chore_date,
                    entity_id,
                    err,
                )

    async def handle_offset_date(call: ServiceCall) -> None:
        """Handle the offset_date service call."""
        entity_ids = call.data.get(CONF_ENTITY_ID, [])
        offset = call.data.get(const.CONF_OFFSET)
        chore_date = call.data.get(const.CONF_DATE, None)
        for entity_id in entity_ids:
            LOGGER.debug(
                "called offset_date %s by %d days for %s",
                chore_date,
                offset,
                entity_id,
            )
            try:
                entity = hass.data[const.DOMAIN][const.SENSOR_PLATFORM][entity_id]
                await entity.offset_date(offset, chore_date)
            except (TypeError, KeyError) as err:
                LOGGER.error("Failed offsetting date for %s - %s", entity_id, err)
                break

    async def handle_update_state(call: ServiceCall) -> None:
        """Handle the update_state service call."""
        entity_ids = call.data.get(CONF_ENTITY_ID, [])
        for entity_id in entity_ids:
            LOGGER.debug("called update_state for %s", entity_id)
            try:
                entity = hass.data[const.DOMAIN][const.SENSOR_PLATFORM][entity_id]
                entity.update_state()
            except KeyError as err:
                LOGGER.error("Failed updating state for %s - %s", entity_id, err)

    async def handle_complete_chore(call: ServiceCall) -> None:
        """Handle the complete_chore service call."""
        entity_ids = call.data.get(CONF_ENTITY_ID, [])
        last_completed = call.data.get(const.ATTR_LAST_COMPLETED, helpers.now())
        for entity_id in entity_ids:
            LOGGER.debug("called complete for %s", entity_id)
            try:
                entity = hass.data[const.DOMAIN][const.SENSOR_PLATFORM][entity_id]
                entity.last_completed = dt_util.as_local(last_completed)
                entity.update_state()
            except KeyError as err:
                LOGGER.error(
                    "Failed setting last completed for %s - %s", entity_id, err
                )

    hass.data.setdefault(const.DOMAIN, {})
    hass.data[const.DOMAIN].setdefault(const.SENSOR_PLATFORM, {})
    hass.services.async_register(
        const.DOMAIN,
        "complete",
        handle_complete_chore,
        schema=COMPLETE_NOW_SCHEMA,
    )
    hass.services.async_register(
        const.DOMAIN,
        "update_state",
        handle_update_state,
        schema=UPDATE_STATE_SCHEMA,
    )
    hass.services.async_register(
        const.DOMAIN, "add_date", handle_add_date, schema=ADD_DATE_SCHEMA
    )
    hass.services.async_register(
        const.DOMAIN,
        "remove_date",
        handle_remove_date,
        schema=REMOVE_DATE_SCHEMA,
    )
    hass.services.async_register(
        const.DOMAIN, "offset_date", handle_offset_date, schema=OFFSET_DATE_SCHEMA
    )
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    LOGGER.debug(
        "Setting %s (%s) from ConfigFlow",
        config_entry.title,
        config_entry.options[const.CONF_FREQUENCY],
    )
    config_entry.add_update_listener(update_listener)
    # Add sensor
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(
            config_entry, const.SENSOR_PLATFORM
        )
    )
    return True


async def async_remove_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Handle removal of an entry."""
    try:
        await hass.config_entries.async_forward_entry_unload(
            config_entry, const.SENSOR_PLATFORM
        )
        LOGGER.info("Successfully removed sensor from the chore_helper integration")
    except ValueError:
        pass


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener - to re-create device after options update."""
    await hass.config_entries.async_forward_entry_unload(entry, const.SENSOR_PLATFORM)
    hass.async_add_job(
        hass.config_entries.async_forward_entry_setup(entry, const.SENSOR_PLATFORM)
    )
