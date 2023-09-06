"""The Tinxy integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.const import Platform

from .const import CONF_API_KEY, DOMAIN, TINXY_BACKEND
from .tinxycloud import TinxyCloud, TinxyHostConfiguration
from .coordinator import TinxyUpdateCoordinator

# List of supported platforms
PLATFORMS: list[Platform] = [Platform.SWITCH, Platform.LIGHT, Platform.FAN]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tinxy from a config entry."""
    # Ensure the DOMAIN data is initialized
    hass.data.setdefault(DOMAIN, {})

    # Create an HTTP session
    web_session = async_get_clientsession(hass)

    # Initialize Tinxy API
    host_config = TinxyHostConfiguration(
        api_token=entry.data[CONF_API_KEY], api_url=TINXY_BACKEND
    )
    api = TinxyCloud(host_config=host_config, web_session=web_session)
    await api.sync_devices()

    # Create and populate coordinator
    coordinator = TinxyUpdateCoordinator(hass, api)
    hass.data[DOMAIN][entry.entry_id] = api, coordinator

    # Forward entry setup to supported platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms and pop the entry data
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
