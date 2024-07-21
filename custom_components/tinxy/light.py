"""Example integration using DataUpdateCoordinator."""

import logging
from typing import Any
import math

from homeassistant.components.light import LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.light import (
    LightEntity,
    ColorMode,
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
)

from .const import DOMAIN
from .coordinator import TinxyUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up Tinxy light entities from a config entry."""
    apidata, coordinator = hass.data[DOMAIN][entry.entry_id]

    await coordinator.async_config_entry_first_refresh()
    switches = []

    status_list = {}
    all_devices = apidata.list_lights()

    _LOGGER.error(all_devices)
    result = await apidata.get_all_status()

    for device in all_devices:
        if device["id"] in result:
            status_list[device["id"]] = {**device, **result[device["id"]]}

    for device in status_list.values():
        switches.append(TinxyLight(coordinator, apidata, device["id"]))

    async_add_entities(switches)


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
        self.data_brightness = math.floor(
            (device_data.get("brightness", 0) / 100) * 255
        )
        self.data_tempcolor = device_data.get("colorTemperatureInKelvin", None)
        self.data_color_mode = (
            ColorMode.COLOR_TEMP
            if "colorTemperatureInKelvin" in device_data
            else ColorMode.BRIGHTNESS
        )

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
        return self.coordinator.data[self.idx].get("colorTemperatureInKelvin")

    @property
    def device_info(self) -> dict:
        """Return the device info."""
        return self.coordinator.data[self.idx]["device"]

    @property
    def brightness(self) -> int:
        """Return the brightness of the light."""
        return math.floor(
            (self.coordinator.data[self.idx].get("brightness", 0) / 100) * 255
        )

    @property
    def supported_color_modes(self) -> list[str]:
        """Return the supported color modes."""
        if "colorTemperatureInKelvin" in self.coordinator.data[self.idx]:
            return [ColorMode.COLOR_TEMP]
        return [ColorMode.BRIGHTNESS]

    @property
    def color_mode(self) -> str:
        """Return the color mode."""
        return self.data_color_mode

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        _LOGGER.warning(kwargs)

        brightness = kwargs.get(ATTR_BRIGHTNESS, self.data_brightness)
        real_brightness = math.floor((brightness / 255) * 100) if brightness else None

        if self.data_color_mode == ColorMode.COLOR_TEMP:
            color_temp_kelvin = kwargs.get(ATTR_COLOR_TEMP_KELVIN, self.data_tempcolor)
        else:
            color_temp_kelvin = None

        reponse_data = await self.api.set_device_state(
            itemid=self.coordinator.data[self.idx]["device_id"],
            device_number=str(self.coordinator.data[self.idx]["relay_no"]),
            state=1,
            brightness=real_brightness,
            color_temp=color_temp_kelvin,
        )
        _LOGGER.error(msg=reponse_data)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        brightness = kwargs.get(ATTR_BRIGHTNESS, self.data_brightness)
        real_brightness = math.floor((brightness / 255) * 100) if brightness else None

        if self.data_color_mode == ColorMode.COLOR_TEMP:
            color_temp_kelvin = kwargs.get(ATTR_COLOR_TEMP_KELVIN, self.data_tempcolor)
        else:
            color_temp_kelvin = None

        reponse_data = await self.api.set_device_state(
            itemid=self.coordinator.data[self.idx]["device_id"],
            device_number=str(self.coordinator.data[self.idx]["relay_no"]),
            state=0,
            brightness=real_brightness,
            color_temp=color_temp_kelvin,
        )
        _LOGGER.error(msg=reponse_data)
        await self.coordinator.async_request_refresh()
