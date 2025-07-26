"""
Coordinator for Tinxy Home Assistant integration.

Handles periodic data updates from the Tinxy API and manages device status lookup.
Follows Home Assistant best practices for custom components.
"""


from datetime import timedelta
import logging
from typing import Any, Dict
import async_timeout

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.debounce import Debouncer

from .tinxycloud import TinxyAuthenticationException, TinxyException

# Module-level logger
_LOGGER = logging.getLogger(__name__)

# Constants for configuration
UPDATE_INTERVAL_SECONDS: int = 7
REQUEST_REFRESH_DELAY: float = 0.35
API_TIMEOUT_SECONDS: int = 10



class TinxyUpdateCoordinator(DataUpdateCoordinator):
    """
    Coordinates updates from the Tinxy API for Home Assistant entities.

    Periodically fetches device status and merges device info for fast entity lookup.
    Handles authentication and API errors gracefully.
    """

    def __init__(self, hass: HomeAssistant, api_client: Any) -> None:
        """
        Initialize the TinxyUpdateCoordinator.

        Args:
            hass (HomeAssistant): The Home Assistant instance.
            api_client (Any): The Tinxy API client instance.
        """
        super().__init__(
            hass,
            _LOGGER,
            name="Tinxy",
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
            request_refresh_debouncer=Debouncer(
                hass,
                _LOGGER,
                cooldown=REQUEST_REFRESH_DELAY,
                immediate=False,
            ),
        )
        self.hass: HomeAssistant = hass
        self.api_client: Any = api_client
        # Fetch all devices once at startup; assumes device list is static
        self.all_devices: list[dict] = self.api_client.list_all_devices()

    async def _async_update_data(self) -> Dict[str, dict]:
        """
        Fetch and merge device status from the Tinxy API.

        Returns:
            Dict[str, dict]: Mapping of device IDs to merged device info and status.

        Raises:
            ConfigEntryAuthFailed: If authentication fails.
            UpdateFailed: For other API errors.
        """
        try:
            async with async_timeout.timeout(API_TIMEOUT_SECONDS):
                status_by_id: Dict[str, dict] = {}
                # Fetch latest status for all devices
                status_result: dict = await self.api_client.get_all_status()

                for device in self.all_devices:
                    device_id = device.get("id")
                    if device_id in status_result:
                        # Merge static device info with dynamic status
                        status_by_id[device_id] = {**device, **status_result[device_id]}
                    else:
                        # Log warning if device status is missing
                        _LOGGER.warning(f"No status found for device ID: {device_id}")

                _LOGGER.debug(f"Fetched status for {len(status_by_id)} devices.")
                return status_by_id
        except TinxyAuthenticationException as auth_err:
            _LOGGER.error("Authentication failed with Tinxy API: %s", auth_err)
            raise ConfigEntryAuthFailed from auth_err
        except TinxyException as api_err:
            _LOGGER.error("Error communicating with Tinxy API: %s", api_err)
            raise UpdateFailed(f"Error communicating with API: {api_err}") from api_err
        except Exception as exc:
            _LOGGER.exception("Unexpected error during Tinxy data update: %s", exc)
            raise UpdateFailed(f"Unexpected error: {exc}") from exc
