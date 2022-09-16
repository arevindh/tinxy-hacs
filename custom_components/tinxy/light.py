from __future__ import annotations
import logging
import math
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from bisect import bisect_right
from types import NoneType
from typing import Any, Callable, Dict, Optional
from .tinxycloud import TinxyCloud
from homeassistant.components.light import LightEntity, ColorMode, ATTR_BRIGHTNESS, COLOR_MODE_ONOFF, COLOR_MODE_BRIGHTNESS
from homeassistant.components.light import PLATFORM_SCHEMA
from homeassistant.helpers.typing import (
    ConfigType,
    DiscoveryInfoType,
    HomeAssistantType,
)

from .const import DOMAIN, MIN_TIME_BETWEEN_UPDATES, CONF_API_KEY

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
    lights = []
    api_key = config.get(CONF_API_KEY)
    hub = TinxyCloud(api_key)
    await hub.sync_devices()
    th_devices = hub.list_lights()
    # _LOGGER.error(json.dumps(th_devices))
    for th_device in th_devices:
        lights.append(TinxyLight(hub, th_device))
    async_add_entities(lights, update_before_add=True)
    return lights


class TinxyLight(LightEntity):
    def __init__(self, hub, t_device) -> None:
        super().__init__()
        self.is_available = True
        self._is_on = False
        self.hub = hub
        self.t_device = t_device
        self._brightness = 0

    @property
    def brightness(self):
        return self._brightness

    @property
    def supported_color_modes(self):
        return [COLOR_MODE_ONOFF, COLOR_MODE_BRIGHTNESS]

    @property
    def color_mode(self):
        return ColorMode.BRIGHTNESS

    @property
    def available(self):
        return self.is_available

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
        """should poll"""
        return True

    @property
    def is_on(self):
        """If the switch is currently on or off."""
        # self.read_status()
        return self._is_on

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        real_brightness = None
        if ATTR_BRIGHTNESS in kwargs:
            brightness = int(kwargs[ATTR_BRIGHTNESS])
            real_brightness = math.floor((brightness/255)*100)            
        await self.hub.set_device_state(
            self.t_device['device_id'], str(self.t_device['relay_no']), 1, real_brightness)
        await self.async_update()

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        # self._is_on = False
        await self.hub.set_device_state(
            self.t_device['device_id'], str(self.t_device['relay_no']), 0)
        await self.async_update()

    async def async_update(self, **kwargs):
        """Update states via poll"""
        resp = await self.hub.get_device_state(self.t_device['device_id'], str(self.t_device['relay_no']))
        if resp['state'] == "ON":
            self._is_on = True
        else:
            self._is_on = False
        if resp['status'] == 1:
            self.is_available = True
        else:
            self.is_available = False

        if resp['brightness'] != NoneType:
            self._brightness = math.floor((resp['brightness']/100)*255)
