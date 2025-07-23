"""Tinxy switch platform."""
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Tinxy switch entities from a config entry."""
    apidata, coordinator = hass.data[DOMAIN][entry.entry_id]

    await coordinator.async_config_entry_first_refresh()
    switches = []

    status_list = {}

    all_devices = apidata.list_switches()
    result = await apidata.get_all_status()

    for device in all_devices:
        if device["id"] in result:
            status_list[device["id"]] = device | result[device["id"]]

    for th_device in status_list:
        switches.append(TinxySwitch(coordinator, apidata, th_device))

    async_add_entities(switches)


class TinxySwitch(CoordinatorEntity, SwitchEntity):
    """Tinxy switch entity."""

    def __init__(self, coordinator: Any, apidata: Any, idx: str) -> None:
        """Initialize the Tinxy switch."""
        super().__init__(coordinator, context=idx)
        self.idx = idx
        self.coordinator = coordinator
        self.api = apidata

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_is_on = self.coordinator.data[self.idx]["state"]
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
    def is_on(self) -> bool:
        """Return if the switch is currently on or off."""
        return self.coordinator.data[self.idx]["state"]

    @property
    def available(self) -> bool:
        """Return device available status."""
        return True if self.coordinator.data[self.idx]["status"] == 1 else False

    @property
    def device_info(self):
        """Return device information."""
        return self.coordinator.data[self.idx]["device"]

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.api.set_device_state(
            self.coordinator.data[self.idx]["device_id"],
            str(self.coordinator.data[self.idx]["relay_no"]),
            1,
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.api.set_device_state(
            self.coordinator.data[self.idx]["device_id"],
            str(self.coordinator.data[self.idx]["relay_no"]),
            0,
        )
        await self.coordinator.async_request_refresh()
