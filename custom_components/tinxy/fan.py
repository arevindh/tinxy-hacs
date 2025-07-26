
"""
Tinxy Fan Platform for Home Assistant.

This module defines the TinxyFan entity and setup logic for integrating Tinxy fans with Home Assistant.
Follows modern Python and Home Assistant best practices for maintainability and clarity.
"""

from __future__ import annotations
import logging
from typing import Any, TYPE_CHECKING, Dict, List, Optional

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
                # Merge static device info with dynamic status
                merged = {**device, **result[device_id]}
                fans.append(TinxyFan(coordinator, apidata, merged))

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

    def __init__(
        self,
        coordinator: CoordinatorEntity,
        apidata: Any,
        device: Dict[str, Any]
    ) -> None:
        """
        Initialize the Tinxy fan entity.

        Args:
            coordinator: Data update coordinator.
            apidata: TinxyCloud API instance.
            device: Device information and status.
        """
        super().__init__(coordinator)
        self._device: Dict[str, Any] = device
        self.api: Any = apidata
        self._attr_unique_id: Optional[str] = device.get("id")
        self._attr_name: Optional[str] = device.get("name")
        self._attr_icon: Optional[str] = device.get("icon")
        self._attr_device_info: Optional[DeviceInfo] = device.get("device")

    @callback
    def _handle_coordinator_update(self) -> None:
        """
        Handle updated data from the coordinator.
        Called when coordinator data is refreshed.
        """
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """
        Return True if the fan is currently on.
        """
        state = self._get_state("state")
        return bool(state)

    @property
    def available(self) -> bool:
        """
        Return True if the device is available.
        """
        return self._get_state("status") == 1

    @property
    def preset_mode(self) -> Optional[str]:
        """
        Return the current preset mode (Low, Medium, High).
        """
        brightness = self._get_state("brightness")
        # Map brightness to preset mode
        return PERCENT_TO_PRESET.get(brightness, "Low")

    async def async_turn_on(
        self,
        percentage: Optional[int] = None,
        preset_mode: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """
        Turn the fan on, optionally setting a preset mode.

        Args:
            percentage: Not used (for compatibility).
            preset_mode: Desired preset mode.
            **kwargs: Additional arguments.
        """
        mode_setting: Optional[int] = self._calculate_percent(preset_mode) if preset_mode else None
        try:
            await self.api.set_device_state(
                self._device["device_id"],
                str(self._device["relay_no"]),
                1,
                mode_setting,
            )
            _LOGGER.info(
                "Turned on Tinxy fan '%s' with preset mode '%s'.", self._attr_name, preset_mode
            )
        except Exception as exc:
            _LOGGER.error("Failed to turn on Tinxy fan '%s': %s", self._attr_name, exc)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """
        Turn the fan off.

        Args:
            **kwargs: Additional arguments.
        """
        try:
            await self.api.set_device_state(
                self._device["device_id"],
                str(self._device["relay_no"]),
                0,
            )
            _LOGGER.info("Turned off Tinxy fan '%s'.", self._attr_name)
        except Exception as exc:
            _LOGGER.error("Failed to turn off Tinxy fan '%s': %s", self._attr_name, exc)
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """
        Set the preset mode of the fan.

        Args:
            preset_mode: Desired preset mode (Low, Medium, High).
        """
        percent = self._calculate_percent(preset_mode)
        try:
            await self.api.set_device_state(
                self._device["device_id"],
                str(self._device["relay_no"]),
                1,
                percent,
            )
            _LOGGER.info(
                "Set Tinxy fan '%s' to preset mode '%s' (%d%%).", self._attr_name, preset_mode, percent
            )
        except Exception as exc:
            _LOGGER.error("Failed to set preset mode for Tinxy fan '%s': %s", self._attr_name, exc)
        await self.coordinator.async_request_refresh()

    def _calculate_percent(self, preset_mode: Optional[str]) -> int:
        """
        Convert preset mode to brightness percentage.

        Args:
            preset_mode: Preset mode string.
        Returns:
            Corresponding brightness percentage.
        """
        if preset_mode is None:
            return PRESET_TO_PERCENT["Low"]
        return PRESET_TO_PERCENT.get(preset_mode, PRESET_TO_PERCENT["Low"])

    def _get_state(self, key: str) -> Any:
        """
        Safely get a state value from coordinator data or fallback to device dict.

        Args:
            key: State key to retrieve.
        Returns:
            State value or None if not found.
        """
        try:
            return self.coordinator.data[self._device["id"]][key]
        except (KeyError, TypeError) as exc:
            _LOGGER.debug(
                "State key '%s' not found for Tinxy fan '%s': %s. Falling back to device dict.",
                key, self._attr_name, exc
            )
            return self._device.get(key)
