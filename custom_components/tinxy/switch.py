"""
Tinxy Switch Platform for Home Assistant
---------------------------------------
Defines the Tinxy switch entity and setup logic for Home Assistant integration.
Follows modern Python and Home Assistant coding standards for maintainability and clarity.
"""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

# Logger for this module
_LOGGER = logging.getLogger(__name__)

STATE_ON: int = 1
STATE_OFF: int = 0

@dataclass
class TinxySwitchDevice:
    """Dataclass representing a Tinxy switch device."""
    id: str
    name: str
    icon: str
    device_id: str
    relay_no: int
    status: int
    state: int
    device: Dict[str, Any]

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    """
    Set up Tinxy switch entities from a config entry.
    Args:
        hass: Home Assistant instance.
        entry: Config entry for this integration.
        async_add_entities: Callback to add entities to Home Assistant.
    """
    try:
        apidata, coordinator = hass.data[DOMAIN][entry.entry_id]
        await coordinator.async_config_entry_first_refresh()

        all_devices = apidata.list_switches()
        result = await apidata.get_all_status()
        switch_entities: List[TinxySwitch] = []

        for device in all_devices:
            device_id = device["id"]
            if device_id in result:
                merged = {**device, **result[device_id]}
                switch_device = TinxySwitchDevice(
                    id=merged["id"],
                    name=merged.get("name", "Tinxy Switch"),
                    icon=merged.get("icon", "mdi:switch"),
                    device_id=merged["device_id"],
                    relay_no=int(merged["relay_no"]),
                    status=int(merged.get("status", 0)),
                    state=int(merged.get("state", 0)),
                    device=merged.get("device", {})
                )
                switch_entities.append(TinxySwitch(coordinator, apidata, switch_device))

        async_add_entities(switch_entities)
        _LOGGER.info("Added %d Tinxy switch entities.", len(switch_entities))
    except Exception as exc:
        _LOGGER.error("Error setting up Tinxy switch entities: %s", exc)

class TinxySwitch(CoordinatorEntity, SwitchEntity):
    """
    Representation of a Tinxy switch entity in Home Assistant.
    """

    def __init__(self, coordinator: Any, apidata: Any, device: TinxySwitchDevice) -> None:
        """
        Initialize the Tinxy switch entity.
        Args:
            coordinator: Data update coordinator.
            apidata: API data object for Tinxy.
            device: TinxySwitchDevice dataclass instance.
        """
        super().__init__(coordinator, context=device.id)
        self.device = device
        self.coordinator = coordinator
        self.api = apidata

    @callback
    def _handle_coordinator_update(self) -> None:
        """
        Handle updated data from the coordinator.
        Updates the entity state in Home Assistant.
        """
        self._attr_is_on = self.coordinator.data[self.device.id]["state"]
        self.async_write_ha_state()

    @property
    def unique_id(self) -> str:
        """
        Return a unique ID for the entity.
        """
        return self.device.id

    @property
    def icon(self) -> str:
        """
        Return the icon for the entity.
        """
        return self.device.icon

    @property
    def name(self) -> str:
        """
        Return the name of the entity.
        """
        return self.device.name

    @property
    def is_on(self) -> bool:
        """
        Return True if the switch is currently on, False otherwise.
        """
        return self.coordinator.data[self.device.id]["state"] == STATE_ON

    @property
    def available(self) -> bool:
        """
        Return True if the device is available, False otherwise.
        """
        return self.coordinator.data[self.device.id]["status"] == 1

    @property
    def device_info(self) -> Dict[str, Any]:
        """
        Return device information for Home Assistant device registry.
        """
        return self.device.device

    async def async_turn_on(self, **kwargs: Any) -> None:
        """
        Turn the switch on.
        """
        try:
            await self.api.set_device_state(
                self.device.device_id,
                str(self.device.relay_no),
                STATE_ON,
            )
            _LOGGER.info(
                "Turned ON Tinxy switch: %s (relay %s)",
                self.device.device_id,
                self.device.relay_no
            )
        except Exception as exc:
            _LOGGER.error("Failed to turn ON Tinxy switch %s: %s", self.device.id, exc)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """
        Turn the switch off.
        """
        try:
            await self.api.set_device_state(
                self.device.device_id,
                str(self.device.relay_no),
                STATE_OFF,
            )
            _LOGGER.info(
                "Turned OFF Tinxy switch: %s (relay %s)",
                self.device.device_id,
                self.device.relay_no
            )
        except Exception as exc:
            _LOGGER.error("Failed to turn OFF Tinxy switch %s: %s", self.device.id, exc)
        await self.coordinator.async_request_refresh()
