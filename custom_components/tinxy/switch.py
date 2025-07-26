
"""
Tinxy Switch Platform for Home Assistant
---------------------------------------
Defines the Tinxy switch entity and setup logic for Home Assistant integration.
Follows modern Python and Home Assistant coding standards for maintainability and clarity.
"""

import logging
from typing import Any, Dict, List
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

# Logger for this module
LOGGER = logging.getLogger(__name__)

# Constants for device state
STATE_ON: int = 1
STATE_OFF: int = 0

def _merge_device_status(device: Dict[str, Any], status: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge device and status dictionaries for a switch.
    Args:
        device: Device information dictionary.
        status: Status information dictionary.
    Returns:
        Merged dictionary containing device and status info.
    """
    merged = device.copy()
    merged.update(status)
    return merged

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
    except Exception as exc:
        LOGGER.error("Failed to retrieve Tinxy API data or coordinator: %s", exc)
        return

    await coordinator.async_config_entry_first_refresh()
    switches: List[TinxySwitch] = []
    status_list: Dict[str, Dict[str, Any]] = {}

    try:
        all_devices = apidata.list_switches()
        result = await apidata.get_all_status()
    except Exception as exc:
        LOGGER.error("Error fetching Tinxy devices or status: %s", exc)
        return

    # Merge device info and status for each switch
    for device in all_devices:
        device_id = device.get("id")
        if device_id in result:
            status_list[device_id] = _merge_device_status(device, result[device_id])

    # Create TinxySwitch entities for each device
    for device_id, device_data in status_list.items():
        switches.append(TinxySwitch(coordinator, apidata, device_id))

    async_add_entities(switches)

class TinxySwitch(CoordinatorEntity, SwitchEntity):
    """
    Representation of a Tinxy switch entity in Home Assistant.
    """

    def __init__(self, coordinator: Any, apidata: Any, idx: str) -> None:
        """
        Initialize the Tinxy switch entity.
        Args:
            coordinator: Data update coordinator.
            apidata: API data object for Tinxy.
            idx: Device index (ID).
        """
        super().__init__(coordinator, context=idx)
        self.idx: str = idx
        self.coordinator: Any = coordinator
        self.api: Any = apidata

    @callback
    def _handle_coordinator_update(self) -> None:
        """
        Handle updated data from the coordinator.
        Updates the entity state in Home Assistant.
        """
        self._attr_is_on = self.coordinator.data[self.idx]["state"]
        self.async_write_ha_state()

    @property
    def unique_id(self) -> str:
        """
        Return a unique ID for the entity.
        Returns:
            Unique string identifier for the switch.
        """
        return self.coordinator.data[self.idx]["id"]

    @property
    def icon(self) -> str:
        """
        Return the icon for the entity.
        Returns:
            Icon string for the switch.
        """
        return self.coordinator.data[self.idx]["icon"]

    @property
    def name(self) -> str:
        """
        Return the name of the entity.
        Returns:
            Name string for the switch.
        """
        return self.coordinator.data[self.idx]["name"]

    @property
    def is_on(self) -> bool:
        """
        Return True if the switch is currently on, False otherwise.
        Returns:
            Boolean indicating switch state.
        """
        return self.coordinator.data[self.idx]["state"]

    @property
    def available(self) -> bool:
        """
        Return True if the device is available, False otherwise.
        Returns:
            Boolean indicating device availability.
        """
        return self.coordinator.data[self.idx]["status"] == 1

    @property
    def device_info(self) -> Dict[str, Any]:
        """
        Return device information for Home Assistant device registry.
        Returns:
            Dictionary with device information.
        """
        return self.coordinator.data[self.idx]["device"]

    async def async_turn_on(self, **kwargs: Any) -> None:
        """
        Turn the switch on.
        Args:
            kwargs: Additional arguments (unused).
        """
        try:
            await self.api.set_device_state(
                self.coordinator.data[self.idx]["device_id"],
                str(self.coordinator.data[self.idx]["relay_no"]),
                STATE_ON,
            )
            LOGGER.info(
                "Turned ON Tinxy switch: %s (relay %s)",
                self.coordinator.data[self.idx]["device_id"],
                self.coordinator.data[self.idx]["relay_no"]
            )
        except Exception as exc:
            LOGGER.error("Failed to turn ON Tinxy switch %s: %s", self.idx, exc)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """
        Turn the switch off.
        Args:
            kwargs: Additional arguments (unused).
        """
        try:
            await self.api.set_device_state(
                self.coordinator.data[self.idx]["device_id"],
                str(self.coordinator.data[self.idx]["relay_no"]),
                STATE_OFF,
            )
            LOGGER.info(
                "Turned OFF Tinxy switch: %s (relay %s)",
                self.coordinator.data[self.idx]["device_id"],
                self.coordinator.data[self.idx]["relay_no"]
            )
        except Exception as exc:
            LOGGER.error("Failed to turn OFF Tinxy switch %s: %s", self.idx, exc)
        await self.coordinator.async_request_refresh()
