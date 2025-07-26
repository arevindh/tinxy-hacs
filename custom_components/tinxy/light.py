
"""
Tinxy light platform integration for Home Assistant.
Optimized for modern Python and Home Assistant standards.
"""

import logging
import math
from typing import Any, Optional

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

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """
    Set up Tinxy light entities from a config entry.
    """
    apidata, coordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_config_entry_first_refresh()

    all_devices = apidata.list_lights()
    result = await apidata.get_all_status()
    status_list = {
        device["id"]: {**device, **result[device["id"]]}
        for device in all_devices if device["id"] in result
    }

    async_add_entities([
        TinxyLight(coordinator, apidata, device["id"])
        for device in status_list.values()
    ])


class TinxyLight(CoordinatorEntity, LightEntity):

    """
    Representation of a Tinxy light entity.
    """

    def __init__(
        self,
        coordinator: TinxyUpdateCoordinator,
        apidata: Any,
        device_id: str,
    ) -> None:
        super().__init__(coordinator)
        self.idx: str = device_id
        self.api: Any = apidata

        device_data = self.coordinator.data[self.idx]
        self._data_brightness: Optional[int] = None
        self._data_tempcolor: Optional[int] = None

        traits = device_data.get("traits", [])
        if (
            "action.devices.traits.ColorSetting" in traits
            and "action.devices.traits.Brightness" in traits
        ):
            self._data_color_mode = ColorMode.COLOR_TEMP
            self._data_tempcolor = device_data.get("colorTemperatureInKelvin", 6952)
        elif "action.devices.traits.Brightness" in traits:
            self._data_color_mode = ColorMode.BRIGHTNESS
            self._data_brightness = math.floor(
                (device_data.get("brightness", 0) / 100) * 255
            )
        else:
            self._data_color_mode = ColorMode.ONOFF


    @callback
    def _handle_coordinator_update(self) -> None:
        """
        Handle updated data from the coordinator.
        """
        self._attr_is_on = bool(self.coordinator.data[self.idx]["state"])
        self.async_write_ha_state()


    @property
    def unique_id(self) -> str:
        """Return the unique ID of the light."""
        return self.coordinator.data[self.idx]["id"]


    @property
    def icon(self) -> Optional[str]:
        """Return the icon of the light."""
        return self.coordinator.data[self.idx].get("icon")


    @property
    def name(self) -> Optional[str]:
        """Return the name of the light."""
        return self.coordinator.data[self.idx].get("name")


    @property
    def is_on(self) -> bool:
        """Return true if the light is on."""
        return bool(self.coordinator.data[self.idx]["state"])


    @property
    def available(self) -> bool:
        """Return true if the light is available."""
        return self.coordinator.data[self.idx].get("status") == 1


    @property
    def max_color_temp_kelvin(self) -> int:
        """Return the maximum color temperature in Kelvin."""
        return 6952


    @property
    def min_color_temp_kelvin(self) -> int:
        """Return the minimum color temperature in Kelvin."""
        return 2200


    @property
    def color_temp_kelvin(self) -> Optional[int]:
        """Return the color temperature in Kelvin."""
        if self._data_color_mode == ColorMode.COLOR_TEMP:
            return self.coordinator.data[self.idx].get("colorTemperatureInKelvin", 6952)
        return None


    @property
    def device_info(self) -> dict:
        """Return the device info."""
        return self.coordinator.data[self.idx]["device"]


    @property
    def brightness(self) -> Optional[int]:
        """Return the brightness of the light."""
        if self._data_color_mode == ColorMode.BRIGHTNESS:
            return math.floor(
                (self.coordinator.data[self.idx].get("brightness", 0) / 100) * 255
            )
        return None


    @property
    def supported_color_modes(self) -> list[str]:
        """Return the supported color modes."""
        return [self._data_color_mode]


    @property
    def color_mode(self) -> str:
        """Return the color mode."""
        return self._data_color_mode


    async def async_turn_on(self, **kwargs: Any) -> None:
        """
        Turn the light on.
        """
        brightness = kwargs.get(ATTR_BRIGHTNESS, self._data_brightness)
        real_brightness = math.floor((brightness / 255) * 100) if brightness is not None else None
        color_temp_kelvin = kwargs.get(ATTR_COLOR_TEMP_KELVIN)

        await self.api.set_device_state(
            item_id=self.coordinator.data[self.idx]["device_id"],
            device_number=str(self.coordinator.data[self.idx]["relay_no"]),
            state=1,
            brightness=real_brightness,
            color_temp=color_temp_kelvin,
        )
        await self.coordinator.async_request_refresh()


    async def async_turn_off(self, **kwargs: Any) -> None:
        """
        Turn the light off.
        """
        brightness = kwargs.get(ATTR_BRIGHTNESS, self._data_brightness)
        real_brightness = math.floor((brightness / 255) * 100) if brightness is not None else None
        color_temp_kelvin = kwargs.get(ATTR_COLOR_TEMP_KELVIN)

        await self.api.set_device_state(
            item_id=self.coordinator.data[self.idx]["device_id"],
            device_number=str(self.coordinator.data[self.idx]["relay_no"]),
            state=0,
            brightness=real_brightness,
            color_temp=color_temp_kelvin,
        )
        await self.coordinator.async_request_refresh()
