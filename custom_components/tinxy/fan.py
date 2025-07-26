"""Tinxy fan platform."""
from __future__ import annotations
import logging
from typing import Any, TYPE_CHECKING

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


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Tinxy fan entities from a config entry."""
    apidata: TinxyCloud
    coordinator = hass.data[DOMAIN][entry.entry_id][1]
    await coordinator.async_config_entry_first_refresh()

    all_devices = hass.data[DOMAIN][entry.entry_id][0].list_fans()
    result = await hass.data[DOMAIN][entry.entry_id][0].get_all_status()

    fans: list[TinxyFan] = []
    for device in all_devices:
        device_id = device["id"]
        if device_id in result:
            merged = {**device, **result[device_id]}
            fans.append(TinxyFan(coordinator, hass.data[DOMAIN][entry.entry_id][0], merged))

    async_add_entities(fans, update_before_add=True)


class TinxyFan(CoordinatorEntity, FanEntity):
    """Representation of a Tinxy fan entity."""

    _attr_should_poll = False
    _attr_preset_modes: list[str] = ["Low", "Medium", "High"]
    _attr_supported_features: FanEntityFeature = (
        FanEntityFeature.PRESET_MODE | FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator: Any, apidata: Any, device: dict[str, Any]) -> None:
        """Initialize the Tinxy fan."""
        super().__init__(coordinator)
        self._device = device
        self.api = apidata
        self._attr_unique_id = device.get("id")
        self._attr_name = device.get("name")
        self._attr_icon = device.get("icon")
        self._attr_device_info = device.get("device")

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return if the fan is currently on or off."""
        return self._get_state("state")

    @property
    def available(self) -> bool:
        """Return device available status."""
        return self._get_state("status") == 1

    @property
    def preset_mode(self) -> str | None:
        """Return current preset mode."""
        brightness = self._get_state("brightness")
        if brightness == 100:
            return "High"
        if brightness == 66:
            return "Medium"
        return "Low"

    async def async_turn_on(self, percentage: int | None = None, preset_mode: str | None = None, **kwargs: Any) -> None:
        """Turn the fan on."""
        mode_setting = self._calculate_percent(preset_mode) if preset_mode else None
        await self.api.set_device_state(
            self._device["device_id"],
            str(self._device["relay_no"]),
            1,
            mode_setting,
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the fan off."""
        await self.api.set_device_state(
            self._device["device_id"],
            str(self._device["relay_no"]),
            0,
        )
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan."""
        await self.api.set_device_state(
            self._device["device_id"],
            str(self._device["relay_no"]),
            1,
            self._calculate_percent(preset_mode),
        )
        await self.coordinator.async_request_refresh()

    def _calculate_percent(self, preset_mode: str | None) -> int:
        """Calculate brightness percentage for preset mode."""
        if preset_mode == "High":
            return 100
        if preset_mode == "Medium":
            return 66
        return 33

    def _get_state(self, key: str) -> Any:
        """Safely get state value from coordinator data."""
        try:
            return self.coordinator.data[self._device["id"]][key]
        except (KeyError, TypeError):
            return self._device.get(key)
