"""Tinxy Data Update Coordinator"""

from datetime import timedelta
import logging
import async_timeout

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.debounce import Debouncer

from .tinxycloud import TinxyAuthenticationException, TinxyException


_LOGGER = logging.getLogger(__name__)
REQUEST_REFRESH_DELAY = 0.35
API_TIMEOUT = 10  # seconds


class TinxyUpdateCoordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    def __init__(self, hass: HomeAssistant, my_api) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Tinxy",
            update_interval=timedelta(seconds=7),
            request_refresh_debouncer=Debouncer(
                hass, _LOGGER, cooldown=REQUEST_REFRESH_DELAY, immediate=False
            ),
        )
        self.my_api = my_api
        # First self sync
        self.all_devices = self.my_api.list_all_devices()

    async def _async_update_data(self) -> dict:
        """Fetch data from API endpoint."""
        try:
            async with async_timeout.timeout(API_TIMEOUT):
                # Fetch fresh data from API
                self.all_devices = self.my_api.list_all_devices()

                # Initialize an empty status list
                status_list = {}

                # Get the status of all devices from the API
                result = await self.my_api.get_all_status()

                # Update the status list based on the fetched results
                for device in self.all_devices:
                    device_id = device["id"]
                    if device_id in result:
                        status_list[device_id] = {**device, **result[device_id]}

                return status_list

        except TinxyAuthenticationException as err:
            raise ConfigEntryAuthFailed("Authentication failed") from err

        except TinxyException as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err