"""Tinxy Fan Entity."""
import logging
from typing import Any

from homeassistant.components.fan import (
    FanEntity,
    FanEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Config entry example."""
    # assuming API object stored here by __init__.py
    apidata, coordinator = hass.data[DOMAIN][entry.entry_id]

    await coordinator.async_config_entry_first_refresh()
    fans = []

    status_list = {}

    all_devices = apidata.list_fans()
    result = await apidata.get_all_status()

    for device in all_devices:
        if device["id"] in result:
            status_list[device["id"]] = device | result[device["id"]]

    for th_device in status_list:
        fans.append(TinxySwitch(coordinator, apidata, th_device))

    async_add_entities(fans)


class TinxySwitch(CoordinatorEntity, FanEntity):
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

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_is_on = self.coordinator.data[self.idx]["state"]
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
    def is_on(self) -> bool:
        """If the switch is currently on or off."""
        return self.coordinator.data[self.idx]["state"]

    @property
    def available(self) -> bool:
        """Device available status."""
        return True if self.coordinator.data[self.idx]["status"] == 1 else False

    @property
    def device_info(self) -> DeviceInfo:
        return self.coordinator.data[self.idx]["device"]

    @property
    def preset_modes(self) -> list[str] | None:
        """List all available preset modes"""
        return ["Low", "Medium", "High"]

    @property
    def supported_features(self) -> FanEntityFeature:
        """List all supported features"""
        return FanEntityFeature.PRESET_MODE

    @property
    def preset_mode(self) -> str | None:
        """Get current preset mode"""
        if self.coordinator.data[self.idx]["brightness"] == 100:
            return "High"
        elif self.coordinator.data[self.idx]["brightness"] == 66:
            return "Medium"
        return "Low"

    async def async_turn_on(self, _percentage, preset_mode, **kwargs: Any) -> None:
        """Turn the switch on."""
        # self._is_on = True
        mode_setting = self.calculate_percent(preset_mode) if preset_mode is not None else None

        await self.api.set_device_state(
            self.coordinator.data[self.idx]["device_id"],
            str(self.coordinator.data[self.idx]["relay_no"]),
            1,
            mode_setting ,
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        # self._is_on = False
        await self.api.set_device_state(
            self.coordinator.data[self.idx]["device_id"],
            str(self.coordinator.data[self.idx]["relay_no"]),
            0,
        )
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan."""

        await self.api.set_device_state(
            self.coordinator.data[self.idx]["device_id"],
            str(self.coordinator.data[self.idx]["relay_no"]),
            1,
            self.calculate_percent(preset_mode),
        )
        await self.coordinator.async_request_refresh()

    def calculate_percent(self, preset_mode: str) -> int:
        """Calculate percent"""
        if preset_mode == "High":
            return 100
        elif preset_mode == "Medium":
            return 66
        return 33
