"""Entity for a manually-scheduled chore."""

from __future__ import annotations

from datetime import date

from .chore import Chore
from .const import LOGGER


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
