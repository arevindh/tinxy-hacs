"""The Tinxy integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_API_KEY, DOMAIN, TINXY_BACKEND
from .tinxycloud import TinxyCloud, TinxyHostConfiguration
from .coordinator import TinxyUpdateCoordinator

# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
PLATFORMS: list[Platform] = [Platform.SWITCH, Platform.LIGHT, Platform.FAN]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tinxy from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    web_session = async_get_clientsession(hass)

    host_config = TinxyHostConfiguration(
        api_token=entry.data[CONF_API_KEY], api_url=TINXY_BACKEND
    )

    api = TinxyCloud(host_config=host_config, web_session=web_session)
    await api.sync_devices()

    coordinator = TinxyUpdateCoordinator(hass, api)

    hass.data[DOMAIN][entry.entry_id] = api, coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
