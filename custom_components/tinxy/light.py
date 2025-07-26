

"""
Tinxy Light Platform Integration for Home Assistant

This module provides the Tinxy light entity implementation for Home Assistant,
following modern Python and Home Assistant development standards.
"""


import logging
import math
from typing import Any, Optional, Dict, List
from dataclasses import dataclass


from homeassistant.components.light import (
    LightEntity,
    ColorMode,
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity


from .const import DOMAIN
from .coordinator import TinxyUpdateCoordinator


# Module-level logger
LOGGER = logging.getLogger(__name__)

# Constants for color temperature range
MIN_COLOR_TEMP_KELVIN: int = 2200
MAX_COLOR_TEMP_KELVIN: int = 6952



async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """
    Set up Tinxy light entities from a config entry.

    Args:
        hass: HomeAssistant instance.
        entry: ConfigEntry for this integration.
        async_add_entities: Callback to add entities.
    """
    try:
        apidata, coordinator = hass.data[DOMAIN][entry.entry_id]
        await coordinator.async_config_entry_first_refresh()

        all_devices = apidata.list_lights()
        result = await apidata.get_all_status()
        status_list = {
            device["id"]: {**device, **result[device["id"]]}
            for device in all_devices if device["id"] in result
        }

        entities = [
            TinxyLight(coordinator=coordinator, apidata=apidata, device_id=device["id"])
            for device in status_list.values()
        ]
        async_add_entities(entities)
        LOGGER.info("Tinxy light entities set up: %d devices", len(entities))
    except Exception as exc:
        LOGGER.error("Error setting up Tinxy light entities: %s", exc)



class TinxyLight(CoordinatorEntity, LightEntity):
    """
    Representation of a Tinxy light entity for Home Assistant.
    Handles state, attributes, and commands for Tinxy lights.
    """

    # Entity constants
    DEFAULT_BRIGHTNESS: int = 255

    def __init__(
        self,
        coordinator: TinxyUpdateCoordinator,
        apidata: Any,
        device_id: str,
    ) -> None:
        """
        Initialize a TinxyLight entity.

        Args:
            coordinator: TinxyUpdateCoordinator instance.
            apidata: API data object for Tinxy.
            device_id: Unique device identifier.
        """
        super().__init__(coordinator)
        self.idx: str = device_id
        self.api: Any = apidata

        device_data: Dict[str, Any] = self.coordinator.data[self.idx]
        self._data_brightness: Optional[int] = None
        self._data_tempcolor: Optional[int] = None

        # Determine supported color mode based on device traits
        traits: List[str] = device_data.get("traits", [])
        if (
            "action.devices.traits.ColorSetting" in traits
            and "action.devices.traits.Brightness" in traits
        ):
            self._data_color_mode: str = ColorMode.COLOR_TEMP
            self._data_tempcolor = device_data.get("colorTemperatureInKelvin", MAX_COLOR_TEMP_KELVIN)
        elif "action.devices.traits.Brightness" in traits:
            self._data_color_mode = ColorMode.BRIGHTNESS
            self._data_brightness = math.floor(
                (device_data.get("brightness", 0) / 100) * self.DEFAULT_BRIGHTNESS
            )
        else:
            self._data_color_mode = ColorMode.ONOFF



    @callback
    def _handle_coordinator_update(self) -> None:
        """
        Handle updated data from the coordinator.
        Updates the entity state in Home Assistant.
        """
        self._attr_is_on = bool(self.coordinator.data[self.idx]["state"])
        self.async_write_ha_state()



    @property
    def unique_id(self) -> str:
        """
        Return the unique ID of the light entity.
        """
        return self.coordinator.data[self.idx]["id"]



    @property
    def icon(self) -> Optional[str]:
        """
        Return the icon for the light entity, if available.
        """
        return self.coordinator.data[self.idx].get("icon")



    @property
    def name(self) -> Optional[str]:
        """
        Return the name of the light entity.
        """
        return self.coordinator.data[self.idx].get("name")



    @property
    def is_on(self) -> bool:
        """
        Return True if the light is currently on.
        """
        return bool(self.coordinator.data[self.idx]["state"])



    @property
    def available(self) -> bool:
        """
        Return True if the light is available (status == 1).
        """
        return self.coordinator.data[self.idx].get("status") == 1



    @property
    def max_color_temp_kelvin(self) -> int:
        """
        Return the maximum color temperature in Kelvin.
        """
        return MAX_COLOR_TEMP_KELVIN



    @property
    def min_color_temp_kelvin(self) -> int:
        """
        Return the minimum color temperature in Kelvin.
        """
        return MIN_COLOR_TEMP_KELVIN



    @property
    def color_temp_kelvin(self) -> Optional[int]:
        """
        Return the color temperature in Kelvin, if supported.
        """
        if self._data_color_mode == ColorMode.COLOR_TEMP:
            return self.coordinator.data[self.idx].get("colorTemperatureInKelvin", MAX_COLOR_TEMP_KELVIN)
        return None



    @property
    def device_info(self) -> Dict[str, Any]:
        """
        Return the device info dictionary for Home Assistant device registry.
        """
        return self.coordinator.data[self.idx]["device"]



    @property
    def brightness(self) -> Optional[int]:
        """
        Return the brightness of the light (0-255), if supported.
        """
        if self._data_color_mode == ColorMode.BRIGHTNESS:
            # Convert brightness from 0-100 to 0-255 scale
            return math.floor(
                (self.coordinator.data[self.idx].get("brightness", 0) / 100) * self.DEFAULT_BRIGHTNESS
            )
        return None



    @property
    def supported_color_modes(self) -> List[str]:
        """
        Return a list of supported color modes for this light.
        """
        return [self._data_color_mode]



    @property
    def color_mode(self) -> str:
        """
        Return the current color mode of the light.
        """
        return self._data_color_mode



    async def async_turn_on(self, **kwargs: Any) -> None:
        """
        Turn the light on, optionally setting brightness and color temperature.

        Args:
            **kwargs: Optional attributes (brightness, color_temp_kelvin).
        """
        brightness: Optional[int] = kwargs.get(ATTR_BRIGHTNESS, self._data_brightness)
        color_temp_kelvin: Optional[int] = kwargs.get(ATTR_COLOR_TEMP_KELVIN)

        # Convert brightness from 0-255 to 0-100 scale for API
        real_brightness: Optional[int] = (
            math.floor((brightness / self.DEFAULT_BRIGHTNESS) * 100)
            if brightness is not None else None
        )

        try:
            await self.api.set_device_state(
                item_id=self.coordinator.data[self.idx]["device_id"],
                device_number=str(self.coordinator.data[self.idx]["relay_no"]),
                state=1,
                brightness=real_brightness,
                color_temp=color_temp_kelvin,
            )
            LOGGER.info(
                "Turned ON Tinxy light %s (brightness=%s, color_temp=%s)",
                self.idx, real_brightness, color_temp_kelvin
            )
        except Exception as exc:
            LOGGER.error("Failed to turn ON Tinxy light %s: %s", self.idx, exc)
        await self.coordinator.async_request_refresh()



    async def async_turn_off(self, **kwargs: Any) -> None:
        """
        Turn the light off, optionally setting brightness and color temperature.

        Args:
            **kwargs: Optional attributes (brightness, color_temp_kelvin).
        """
        brightness: Optional[int] = kwargs.get(ATTR_BRIGHTNESS, self._data_brightness)
        color_temp_kelvin: Optional[int] = kwargs.get(ATTR_COLOR_TEMP_KELVIN)

        # Convert brightness from 0-255 to 0-100 scale for API
        real_brightness: Optional[int] = (
            math.floor((brightness / self.DEFAULT_BRIGHTNESS) * 100)
            if brightness is not None else None
        )

        try:
            await self.api.set_device_state(
                item_id=self.coordinator.data[self.idx]["device_id"],
                device_number=str(self.coordinator.data[self.idx]["relay_no"]),
                state=0,
                brightness=real_brightness,
                color_temp=color_temp_kelvin,
            )
            LOGGER.info(
                "Turned OFF Tinxy light %s (brightness=%s, color_temp=%s)",
                self.idx, real_brightness, color_temp_kelvin
            )
        except Exception as exc:
            LOGGER.error("Failed to turn OFF Tinxy light %s: %s", self.idx, exc)
        await self.coordinator.async_request_refresh()
