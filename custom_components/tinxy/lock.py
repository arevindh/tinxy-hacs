"""Tinxy lock platform."""

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.lock import (
    LockEntityFeature,
    LockEntity
)

from .const import DOMAIN
from .coordinator import TinxyUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up Tinxy lock entities from a config entry."""
    apidata, coordinator = hass.data[DOMAIN][entry.entry_id]

    await coordinator.async_config_entry_first_refresh()
    locks = []

    status_list = {}

    all_devices = apidata.list_locks()
    result = await apidata.get_all_status()

    for device in all_devices:
        if device["id"] in result:
            status_list[device["id"]] = device | result[device["id"]]

    for th_device in status_list:
        locks.append(TinxyLock(coordinator, apidata, th_device))

    async_add_entities(locks)


class TinxyLock(CoordinatorEntity, LockEntity):
    """Tinxy lock entity."""

    def __init__(self, coordinator, apidata, idx) -> None:
        """Initialize the Tinxy lock."""
        super().__init__(coordinator, context=idx)
        self.idx = idx
        self.coordinator = coordinator
        self.api = apidata

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_is_open = self.coordinator.data[self.idx]["door"] == "OPEN"
        self.async_write_ha_state()

    @property
    def unique_id(self) -> str:
        """Return unique ID for the entity."""
        return self.coordinator.data[self.idx]["id"]

    @property
    def icon(self) -> str:
        """Return icon for entity."""
        return self.coordinator.data[self.idx]["icon"]

    @property
    def name(self) -> str:
        """Return name of the entity."""
        return self.coordinator.data[self.idx]["name"]

    @property
    def is_locked(self) -> bool:
        """Return true if the lock is locked."""
        return self.coordinator.data[self.idx].get("door", self.coordinator.data[self.idx]["state"]) != "OPEN"

    @property
    def is_open(self) -> bool:
        """Return true if the lock is open."""
        return self.coordinator.data[self.idx].get("door", self.coordinator.data[self.idx]["state"]) == "OPEN"

    @property
    def available(self) -> bool:
        """Return device available status."""
        return True if self.coordinator.data[self.idx]["status"] == 1 else False

    @property
    def device_info(self):
        """Return device information."""
        return self.coordinator.data[self.idx]["device"]

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the lock."""
        await self.api.set_device_state(
            self.coordinator.data[self.idx]["device_id"],
            str(self.coordinator.data[self.idx]["relay_no"]),
            1,
        )

        await self.coordinator.async_request_refresh()

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the lock."""
        await self.api.set_device_state(
            self.coordinator.data[self.idx]["device_id"],
            str(self.coordinator.data[self.idx]["relay_no"]),
            0,
        )
        await self.coordinator.async_request_refresh()