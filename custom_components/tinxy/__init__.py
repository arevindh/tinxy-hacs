"""
Tinxy Home Assistant Integration
This module sets up and manages the Tinxy integration for Home Assistant.
"""

from __future__ import annotations
from typing import Any

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, TINXY_BACKEND
from .tinxycloud import TinxyCloud, TinxyHostConfiguration
from .coordinator import TinxyUpdateCoordinator

# Logger for this module
LOGGER = logging.getLogger(__name__)

# Supported platforms for Tinxy devices
PLATFORMS: list[Platform] = [
    Platform.SWITCH,
    Platform.LIGHT,
    Platform.FAN,
    Platform.LOCK,
]

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry
) -> bool:
    """
    Set up Tinxy integration from a config entry.

    Args:
        hass (HomeAssistant): The Home Assistant instance.
        entry (ConfigEntry): The configuration entry for Tinxy.

    Returns:
        bool: True if setup was successful, False otherwise.
    """
    LOGGER.info("Setting up Tinxy integration for entry_id=%s", entry.entry_id)

    # Ensure domain data exists
    hass.data.setdefault(DOMAIN, {})

    # Create web session for API communication
    web_session = async_get_clientsession(hass)

    # Prepare host configuration for TinxyCloud
    host_config = TinxyHostConfiguration(
        api_token=entry.data[CONF_API_KEY],
        api_url=TINXY_BACKEND,
    )

    # Initialize TinxyCloud API
    api = TinxyCloud(host_config=host_config, web_session=web_session)
    try:
        await api.sync_devices()
        LOGGER.info("Successfully synced Tinxy devices for entry_id=%s", entry.entry_id)
    except Exception as exc:
        LOGGER.error("Failed to sync Tinxy devices: %s", exc)
        return False

    # Create update coordinator for device state management
    coordinator = TinxyUpdateCoordinator(hass, api)

    # Store API and coordinator in hass data
    hass.data[DOMAIN][entry.entry_id] = (api, coordinator)

    # Forward setup to supported platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    LOGGER.info("Tinxy integration setup complete for entry_id=%s", entry.entry_id)
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry
) -> bool:
    """
    Unload a Tinxy config entry and clean up resources.

    Args:
        hass (HomeAssistant): The Home Assistant instance.
        entry (ConfigEntry): The configuration entry to unload.

    Returns:
        bool: True if unload was successful, False otherwise.
    """
    LOGGER.info("Unloading Tinxy integration for entry_id=%s", entry.entry_id)
    unload_ok: bool = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        # Remove stored API and coordinator
        hass.data[DOMAIN].pop(entry.entry_id, None)
        LOGGER.info("Tinxy integration unloaded for entry_id=%s", entry.entry_id)
    else:
        LOGGER.warning("Failed to unload Tinxy integration for entry_id=%s", entry.entry_id)
    return unload_ok
