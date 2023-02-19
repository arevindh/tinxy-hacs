from __future__ import annotations
from homeassistant.util.percentage import ordered_list_item_to_percentage, percentage_to_ordered_list_item
import voluptuous as vol
from typing import Any, Callable, Dict, Optional
import requests
import json
import logging
from .tinxycloud import TinxyCloud

from homeassistant.components.fan import FanEntity, SUPPORT_SET_SPEED
from homeassistant.components.fan import PLATFORM_SCHEMA
from homeassistant.helpers.typing import (
    ConfigType,
    DiscoveryInfoType,
    HomeAssistantType,
)
import homeassistant.helpers.config_validation as cv


from .const import DOMAIN, MIN_TIME_BETWEEN_UPDATES, CONF_API_KEY
SPEED_RANGE = (1, 100)
_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = MIN_TIME_BETWEEN_UPDATES

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_API_KEY): cv.string
    }
)


async def async_setup_platform(
    hass: HomeAssistantType,
    config: ConfigType,
    async_add_entities: Callable,
    discovery_info: Optional[DiscoveryInfoType] = None,
) -> None:
    """Set up the sensor platform."""
    fans = []
    api_key = config.get(CONF_API_KEY)
    async_add_entities(fans, update_before_add=True)
    hub = TinxyCloud(api_key)
    await hub.sync_devices()
    th_devices = hub.list_fans()
    for th_device in th_devices:
        fans.append(TinxyFan(hub, th_device))

    async_add_entities(fans, update_before_add=True)


class TinxyFan(FanEntity):
    def __init__(self, hub, t_device) -> None:
        super().__init__()
        self.is_available = True
        self._is_on = False
        self.hub = hub
        self.t_device = t_device
        self._current_speed = 0

    @property
    def device_info(self):
        return self.t_device['device']
        
    @property
    def available(self):
        return self.is_available

    @property
    def unique_id(self):
        return self.t_device['id']

    @property
    def supported_features(self):
        return SUPPORT_SET_SPEED

    @property
    def icon(self):
        return self.t_device['icon']

    @property
    def name(self):
        """Name of the entity."""
        return self.t_device['name']

    @property
    def should_poll(self):
        return True

    @property
    def is_on(self):
        """If the switch is currently on or off."""
        # self.read_status()
        return self._is_on

    @property
    def percentage(self) -> Optional[int]:
        """Return the current speed percentage."""
        return self._current_speed

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        current_state = 1 if self._is_on is True else 0

        if percentage > 1 and percentage <= 33:
            percentage = 33
        elif percentage > 33 and percentage <= 66:
            percentage = 66
        elif percentage > 66:
            percentage = 100

        await self.hub.set_device_state(
            self.t_device['device_id'], str(self.t_device['relay_no']), current_state, percentage)
        await self.async_update()

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        # self._is_on = True
        await self.hub.set_device_state(
            self.t_device['device_id'], str(self.t_device['relay_no']), 1)
        await self.async_update()

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        # self._is_on = False
        await self.hub.set_device_state(
            self.t_device['device_id'], str(self.t_device['relay_no']), 0)
        await self.async_update()

    async def async_update(self, **kwargs):
        resp = await self.hub.get_device_state(self.t_device['device_id'], str(self.t_device['relay_no']))
        if resp['state'] == "ON":
            self._is_on = True
        else:
            self._is_on = False
        if resp['status'] == 1:
            self.is_available = True
        else:
            self.is_available = False
        if resp['brightness'] != None:
            self._current_speed = resp['brightness']
