"""
Tinxy Fan Platform for Home Assistant.

This module defines the TinxyFan entity and setup logic for integrating Tinxy fans with Home Assistant.
Follows modern Python and Home Assistant best practices for maintainability and clarity.
"""

from __future__ import annotations
import logging
from typing import Any, TYPE_CHECKING, Dict, List, Optional
from dataclasses import dataclass

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN

if TYPE_CHECKING:
    from .tinxycloud import TinxyCloud

_LOGGER = logging.getLogger(__name__)


# Preset mode mappings for Tinxy fans
PRESET_MODES: List[str] = ["Low", "Medium", "High"]
PRESET_TO_PERCENT: Dict[str, int] = {
    "Low": 33,
    "Medium": 66,
    "High": 100,
}
PERCENT_TO_PRESET: Dict[int, str] = {
    33: "Low",
    66: "Medium",
    100: "High",
}

@dataclass
class TinxyFanDevice:
    """Dataclass representing a Tinxy fan device."""
    id: str
    name: str
    icon: Optional[str]
    device_id: str
    relay_no: int
    status: int
    state: int
    brightness: int
    device: Dict[str, Any]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    """
    Set up Tinxy fan entities from a config entry.

    Args:
        hass: HomeAssistant instance.
        entry: ConfigEntry for this integration.
        async_add_entities: Callback to add entities.
    """
    try:
        coordinator = hass.data[DOMAIN][entry.entry_id][1]
        apidata: TinxyCloud = hass.data[DOMAIN][entry.entry_id][0]
        await coordinator.async_config_entry_first_refresh()

        all_devices = apidata.list_fans()
        result = await apidata.get_all_status()

        fans: List[TinxyFan] = []
        for device in all_devices:
            device_id = device["id"]
            if device_id in result:
                merged = {**device, **result[device_id]}
                fan_device = TinxyFanDevice(
                    id=merged["id"],
                    name=merged.get("name", "Tinxy Fan"),
                    icon=merged.get("icon"),
                    device_id=merged["device_id"],
                    relay_no=int(merged["relay_no"]),
                    status=int(merged.get("status", 0)),
                    state=int(merged.get("state", 0)),
                    brightness=int(merged.get("brightness", 33)),
                    device=merged.get("device", {})
                )
                fans.append(TinxyFan(coordinator, apidata, fan_device))

        async_add_entities(fans, update_before_add=True)
        _LOGGER.info("Added %d Tinxy fan entities.", len(fans))
    except Exception as exc:
        _LOGGER.error("Error setting up Tinxy fan entities: %s", exc)


class TinxyFan(CoordinatorEntity, FanEntity):
    """
    Representation of a Tinxy fan entity for Home Assistant.
    Handles state, preset modes, and interaction with TinxyCloud API.
    """

    _attr_should_poll: bool = False
    _attr_preset_modes: List[str] = PRESET_MODES
    _attr_supported_features: FanEntityFeature = (
        FanEntityFeature.PRESET_MODE | FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator: CoordinatorEntity, apidata: Any, device: TinxyFanDevice) -> None:
        """
        Initialize the Tinxy fan entity.
        Args:
            coordinator: Data update coordinator.
            apidata: TinxyCloud API instance.
            device: TinxyFanDevice dataclass instance.
        """
        super().__init__(coordinator, context=device.id)
        self.device = device
        self.api = apidata
        self.coordinator = coordinator

    @callback
    def _handle_coordinator_update(self) -> None:
        """
        Handle updated data from the coordinator.
        Called when coordinator data is refreshed.
        """
        self.async_write_ha_state()

    @property
    def unique_id(self) -> Optional[str]:
        """
        Return the unique ID of the fan entity.
        """
        return self.device.id

    @property
    def icon(self) -> Optional[str]:
        """
        Return the icon for the fan entity, if available.
        """
        return self.device.icon

    @property
    def name(self) -> Optional[str]:
        """
        Return the name of the fan entity.
        """
        return self.device.name

    @property
    def is_on(self) -> bool:
        """
        Return True if the fan is currently on.
        """
        return self.coordinator.data[self.device.id]["state"] == 1

    @property
    def available(self) -> bool:
        """
        Return True if the device is available.
        """
        return self.coordinator.data[self.device.id]["status"] == 1

    @property
    def preset_mode(self) -> Optional[str]:
        """
        Return the current preset mode (Low, Medium, High).
        """
        brightness = self.coordinator.data[self.device.id].get("brightness", 33)
        return PERCENT_TO_PRESET.get(brightness, "Low")

    @property
    def device_info(self) -> Optional[DeviceInfo]:
        """
        Return device information for Home Assistant device registry.
        """
        return self.device.device

    async def async_turn_on(
        self,
        percentage: Optional[int] = None,
        preset_mode: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """
        Turn the fan on, optionally setting a preset mode.
        """
        mode_setting: Optional[int] = self._calculate_percent(preset_mode) if preset_mode else None
        try:
            await self.api.set_device_state(
                self.device.device_id,
                str(self.device.relay_no),
                1,
                mode_setting,
            )
            _LOGGER.info(
                "Turned on Tinxy fan '%s' with preset mode '%s'.", self.device.name, preset_mode
            )
        except Exception as exc:
            _LOGGER.error("Failed to turn on Tinxy fan '%s': %s", self.device.name, exc)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """
        Turn the fan off.
        """
        try:
            await self.api.set_device_state(
                self.device.device_id,
                str(self.device.relay_no),
                0,
            )
            _LOGGER.info("Turned off Tinxy fan '%s'.", self.device.name)
        except Exception as exc:
            _LOGGER.error("Failed to turn off Tinxy fan '%s': %s", self.device.name, exc)
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """
        Set the preset mode of the fan.
        """
        percent = self._calculate_percent(preset_mode)
        try:
            await self.api.set_device_state(
                self.device.device_id,
                str(self.device.relay_no),
                1,
                percent,
            )
            _LOGGER.info(
                "Set Tinxy fan '%s' to preset mode '%s' (%d%%).", self.device.name, preset_mode, percent
            )
        except Exception as exc:
            _LOGGER.error("Failed to set preset mode for Tinxy fan '%s': %s", self.device.name, exc)
        await self.coordinator.async_request_refresh()

    def _calculate_percent(self, preset_mode: Optional[str]) -> int:
        """
        Convert preset mode to brightness percentage.
        """
        if preset_mode is None:
            return PRESET_TO_PERCENT["Low"]
        return PRESET_TO_PERCENT.get(preset_mode, PRESET_TO_PERCENT["Low"])
