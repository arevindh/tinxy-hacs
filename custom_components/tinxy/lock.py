"""Example integration using DataUpdateCoordinator."""

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
    """Config entry example."""
    # assuming API object stored here by __init__.py
    apidata, coordinator = hass.data[DOMAIN][entry.entry_id]

    # _LOGGER.error(apidata)

    # Fetch initial data so we have data when entities subscribe
    #
    # If the refresh fails, async_config_entry_first_refresh will
    # raise ConfigEntryNotReady and setup will try again later
    #
    # If you do not want to retry setup on failure, use
    # coordinator.async_refresh() instead
    #
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
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    def __init__(self, coordinator, apidata, idx) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, context=idx)
        self.idx = idx
        self.coordinator = coordinator
        self.api = apidata
        # _LOGGER.warning(
        #     self.coordinator.data[self.idx]["name"]
        #     + " - "
        #     + self.coordinator.data[self.idx]["state"]
        # )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_is_open = self.coordinator.data[self.idx]["door"] == "OPEN"
    
        _LOGGER.error(
            self.coordinator.data[self.idx]
        )

        self.async_write_ha_state()

    @property
    def unique_id(self) -> str:
        """dasdasdasd."""
        return self.coordinator.data[self.idx]["id"]

    @property
    def icon(self) -> str:
        """Icon for entity."""
        return self.coordinator.data[self.idx]["icon"]

    @property
    def name(self) -> str:
        """Name of the entity."""
        return self.coordinator.data[self.idx]["name"]

    @property
    def is_locked(self) -> bool:
        """If the switch is currently on or off."""
        # self.read_status()
        return self.coordinator.data[self.idx]["door"] != "OPEN"
        # return False

    @property
    def is_open(self) -> bool:
        """If the switch is currently on or off."""
        # self.read_status()
        return self.coordinator.data[self.idx]["door"] == "OPEN"
        # return False


    @property
    def available(self) -> bool:
        """Device available status."""
        return True if self.coordinator.data[self.idx]["status"] == 1 else False

    @property
    def device_info(self):
        return self.coordinator.data[self.idx]["device"]

    async def async_unlock(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        # self._is_on = True
        await self.api.set_device_state(
            self.coordinator.data[self.idx]["device_id"],
            str(self.coordinator.data[self.idx]["relay_no"]),
            1,
        )

        await self.coordinator.async_request_refresh()

    async def async_lock(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        # self._is_on = False
        await self.api.set_device_state(
            self.coordinator.data[self.idx]["device_id"],
            str(self.coordinator.data[self.idx]["relay_no"]),
            0,
        )
        await self.coordinator.async_request_refresh()