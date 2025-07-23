"""Tinxy light platform."""

import logging
from typing import Any
import math

from homeassistant.components.light import (
    LightEntity,
    ColorMode,
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TinxyUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up Tinxy light entities from a config entry."""
    apidata, coordinator = hass.data[DOMAIN][entry.entry_id]

    await coordinator.async_config_entry_first_refresh()
    lights = []

    status_list = {}
    all_devices = apidata.list_lights()

    result = await apidata.get_all_status()

    for device in all_devices:
        if device["id"] in result:
            status_list[device["id"]] = {**device, **result[device["id"]]}

    for device in status_list.values():
        lights.append(TinxyLight(coordinator, apidata, device["id"]))

    async_add_entities(lights)


class TinxyLight(CoordinatorEntity, LightEntity):
    """Representation of a Tinxy light."""

    def __init__(
        self, coordinator: TinxyUpdateCoordinator, apidata: Any, device_id: str
    ) -> None:
        """Initialize the Tinxy light."""
        super().__init__(coordinator)
        self.idx = device_id
        self.api = apidata

        device_data = self.coordinator.data[self.idx]
        self.data_brightness = None
        self.data_tempcolor = None

        traits = device_data.get("traits", [])

        if (
            "action.devices.traits.ColorSetting" in traits
            and "action.devices.traits.Brightness" in traits
        ):
            self.data_color_mode = ColorMode.COLOR_TEMP
            self.data_tempcolor = device_data.get("colorTemperatureInKelvin", 6952)
        elif "action.devices.traits.Brightness" in traits:
            self.data_color_mode = ColorMode.BRIGHTNESS
            self.data_brightness = math.floor(
                (device_data.get("brightness", 0) / 100) * 255
            )
        else:
            self.data_color_mode = ColorMode.ONOFF

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_is_on = self.coordinator.data[self.idx]["state"]
        self.async_write_ha_state()

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the light."""
        return self.coordinator.data[self.idx]["id"]

    @property
    def icon(self) -> str:
        """Return the icon of the light."""
        return self.coordinator.data[self.idx]["icon"]

    @property
    def name(self) -> str:
        """Return the name of the light."""
        return self.coordinator.data[self.idx]["name"]

    @property
    def is_on(self) -> bool:
        """Return true if the light is on."""
        return self.coordinator.data[self.idx]["state"]

    @property
    def available(self) -> bool:
        """Return true if the light is available."""
        return self.coordinator.data[self.idx]["status"] == 1

    @property
    def max_color_temp_kelvin(self) -> int:
        """Return the maximum color temperature in Kelvin."""
        return 6952

    @property
    def min_color_temp_kelvin(self) -> int:
        """Return the minimum color temperature in Kelvin."""
        return 2200

    @property
    def color_temp_kelvin(self) -> int:
        """Return the color temperature in Kelvin."""
        if self.data_color_mode == ColorMode.COLOR_TEMP:
            return self.coordinator.data[self.idx].get("colorTemperatureInKelvin", 6952)
        return None

    @property
    def device_info(self) -> dict:
        """Return the device info."""
        return self.coordinator.data[self.idx]["device"]

    @property
    def brightness(self) -> int:
        """Return the brightness of the light."""
        if self.data_color_mode == ColorMode.BRIGHTNESS:
            return math.floor(
                (self.coordinator.data[self.idx].get("brightness", 0) / 100) * 255
            )
        return None

    @property
    def supported_color_modes(self) -> list[str]:
        """Return the supported color modes."""
        return [self.data_color_mode]

    @property
    def color_mode(self) -> str:
        """Return the color mode."""
        return self.data_color_mode

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        brightness = kwargs.get(ATTR_BRIGHTNESS, self.data_brightness)
        real_brightness = math.floor((brightness / 255) * 100) if brightness else None

        color_temp_kelvin = kwargs.get(ATTR_COLOR_TEMP_KELVIN, None)

        await self.api.set_device_state(
            itemid=self.coordinator.data[self.idx]["device_id"],
            device_number=str(self.coordinator.data[self.idx]["relay_no"]),
            state=1,
            brightness=real_brightness,
            color_temp=color_temp_kelvin,
        )

        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        brightness = kwargs.get(ATTR_BRIGHTNESS, self.data_brightness)
        real_brightness = math.floor((brightness / 255) * 100) if brightness else None
        color_temp_kelvin = kwargs.get(ATTR_COLOR_TEMP_KELVIN, None)

        await self.api.set_device_state(
            itemid=self.coordinator.data[self.idx]["device_id"],
            device_number=str(self.coordinator.data[self.idx]["relay_no"]),
            state=0,
            brightness=real_brightness,
            color_temp=color_temp_kelvin,
        )

        await self.coordinator.async_request_refresh()
