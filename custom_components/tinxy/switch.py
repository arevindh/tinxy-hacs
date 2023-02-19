from __future__ import annotations
import voluptuous as vol
from typing import Any, Callable, Dict, Optional
import requests
import json
import logging
from .tinxycloud import TinxyCloud

from homeassistant.components.switch import SwitchEntity
from homeassistant.components.switch import PLATFORM_SCHEMA
from homeassistant.helpers.typing import (
    ConfigType,
    DiscoveryInfoType,
    HomeAssistantType,
)
import homeassistant.helpers.config_validation as cv


from .const import DOMAIN, MIN_TIME_BETWEEN_UPDATES, CONF_API_KEY

SCAN_INTERVAL = MIN_TIME_BETWEEN_UPDATES

_LOGGER = logging.getLogger(__name__)

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
    switches = []
    api_key = config.get(CONF_API_KEY)
    # switches = await hass.async_add_executor_job(sync_devices(api_key))
    async_add_entities(switches, update_before_add=True)
    hub = TinxyCloud(api_key)
    await hub.sync_devices()
    th_devices = hub.list_switches()
    # _LOGGER.error(json.dumps(th_devices))
    for th_device in th_devices:
        switches.append(TinxySwitch(hub, th_device))

    async_add_entities(switches, update_before_add=True)
    return switches


class TinxySwitch(SwitchEntity):
    def __init__(self, hub, t_device) -> None:
        super().__init__()
        self.is_available = True
        self._is_on = False
        self.hub = hub
        self.t_device = t_device

    @property
    def available(self):
        return self.is_available

    @property
    def device_info(self):
        return self.t_device['device']

    @property
    def unique_id(self):
        return self.t_device['id']

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
