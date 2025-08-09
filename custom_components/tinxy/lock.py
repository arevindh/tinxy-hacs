"""
Tinxy Lock Platform for Home Assistant.

This module provides the TinxyLock entity for Home Assistant, enabling control and monitoring of Tinxy smart locks.
Follows best practices for maintainability, readability, and modern Python development.
"""


import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.lock import LockEntity


from .const import DOMAIN


_LOGGER = logging.getLogger(__name__)

# Constants for lock states and device status
LOCK_STATE_OPEN = "OPEN"
LOCK_STATE_LOCKED = "LOCKED"
DEVICE_STATUS_ONLINE = 1

@dataclass
class TinxyLockDevice:
    """Dataclass representing a Tinxy lock device."""
    id: str
    name: str
    icon: str
    device_id: str
    relay_no: int
    status: int
    door: Optional[str]
    state: Optional[str]
    device: Dict[str, Any]



async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    """
    Set up Tinxy lock entities from a config entry.

    Args:
        hass: HomeAssistant instance.
        entry: ConfigEntry for this integration.
        async_add_entities: Callback to add entities.
    """
    apidata, coordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_config_entry_first_refresh()

    # Gather lock devices and their status
    all_devices: List[Dict[str, Any]] = apidata.list_locks()
    status_result: Dict[str, Dict[str, Any]] = await apidata.get_all_status()
    lock_entities: List[TinxyLock] = []

    for device in all_devices:
        device_id = device["id"]
        if device_id in status_result:
            # Merge device info and status
            merged = {**device, **status_result[device_id]}
            lock_device = TinxyLockDevice(
                id=merged["id"],
                name=merged.get("name", "Tinxy Lock"),
                icon=merged.get("icon", "mdi:lock"),
                device_id=merged["device_id"],
                relay_no=int(merged["relay_no"]),
                status=int(merged.get("status", 0)),
                door=merged.get("door"),
                state=merged.get("state"),
                device=merged.get("device", {})
            )
            lock_entities.append(TinxyLock(coordinator, apidata, lock_device))

    async_add_entities(lock_entities)



class TinxyLock(CoordinatorEntity, LockEntity):
    """
    TinxyLock entity for Home Assistant.

    Represents a Tinxy smart lock, providing lock/unlock functionality and state reporting.
    """

    def __init__(self, coordinator: Any, api: Any, device: TinxyLockDevice) -> None:
        """
        Initialize the TinxyLock entity.

        Args:
            coordinator: Data update coordinator.
            api: API object for Tinxy cloud.
            device: TinxyLockDevice dataclass instance.
        """
        super().__init__(coordinator, context=device.id)
        self.device = device
        self.coordinator = coordinator
        self.api = api

    @callback
    def _handle_coordinator_update(self) -> None:
        """
        Handle updated data from the coordinator.
        Updates the entity state when coordinator data changes.
        """
        # Defensive: check for 'door' key
        door_state = self.coordinator.data[self.device.id].get("door")
        self._attr_is_open = door_state == LOCK_STATE_OPEN
        self.async_write_ha_state()

    @property
    def unique_id(self) -> str:
        """
        Return unique ID for the entity.
        """
        return self.device.id

    @property
    def icon(self) -> str:
        """
        Return icon for the entity.
        """
        return self.device.icon

    @property
    def name(self) -> str:
        """
        Return name of the entity.
        """
        return self.device.name

    @property
    def is_locked(self) -> bool:
        """
        Return True if the lock is locked.
        Uses 'door' state if available, otherwise falls back to 'state'.
        """
        data = self.coordinator.data[self.device.id]
        door_state = data.get("door", data.get("state"))
        is_locked = door_state != LOCK_STATE_OPEN
        # Log state for debugging
        _LOGGER.debug(f"Lock {self.device.id} is_locked check: door_state={door_state}, is_locked={is_locked}")
        return is_locked

    @property
    def is_open(self) -> bool:
        """
        Return True if the lock is open.
        """
        data = self.coordinator.data[self.device.id]
        door_state = data.get("door", data.get("state"))
        is_open = door_state == LOCK_STATE_OPEN
        _LOGGER.debug(f"Lock {self.device.id} is_open check: door_state={door_state}, is_open={is_open}")
        return is_open

    @property
    def available(self) -> bool:
        """
        Return device availability status.
        """
        status = self.coordinator.data[self.device.id].get("status", 0)
        available = status == DEVICE_STATUS_ONLINE
        if not available:
            _LOGGER.warning(f"Lock {self.device.id} is offline (status={status})")
        return available

    @property
    def device_info(self) -> Dict[str, Any]:
        """
        Return device information dictionary for Home Assistant.
        """
        return self.device.device

    async def async_unlock(self, **kwargs: Any) -> None:
        """
        Unlock the lock asynchronously.
        Sends unlock command to Tinxy cloud and refreshes coordinator data.
        """
        try:
            await self.api.set_device_state(
                self.device.device_id,
                str(self.device.relay_no),
                1,  # 1 = unlock
            )
            _LOGGER.info(f"Unlock command sent for lock {self.device.id}")
        except Exception as exc:
            _LOGGER.error(f"Failed to unlock lock {self.device.id}: {exc}")
        await self.coordinator.async_request_refresh()

    async def async_lock(self, **kwargs: Any) -> None:
        """
        Lock the lock asynchronously.
        Sends lock command to Tinxy cloud and refreshes coordinator data.
        """
        try:
            await self.api.set_device_state(
                self.device.device_id,
                str(self.device.relay_no),
                0,  # 0 = lock
            )
            _LOGGER.info(f"Lock command sent for lock {self.device.id}")
        except Exception as exc:
            _LOGGER.error(f"Failed to lock lock {self.device.id}: {exc}")
        await self.coordinator.async_request_refresh()