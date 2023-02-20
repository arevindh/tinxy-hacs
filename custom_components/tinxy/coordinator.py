"""Example integration using DataUpdateCoordinator."""

from datetime import timedelta
import logging

import async_timeout

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.debounce import Debouncer

from .tinxycloud import TinxyAuthenticationException, TinxyException

# from homeassistant.exceptions import


_LOGGER = logging.getLogger(__name__)
REQUEST_REFRESH_DELAY = 0.35


class TinxyUpdateCoordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    def __init__(self, hass: HomeAssistant, my_api) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="Tinxy",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=7),
            request_refresh_debouncer=Debouncer(
                hass, _LOGGER, cooldown=REQUEST_REFRESH_DELAY, immediate=False
            ),
        )
        # my_api.list_all
        self.hass = hass
        self.my_api = my_api
        self.all_devices = self.my_api.list_all_devices()

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with async_timeout.timeout(10):
                status_list = {}
                # Grab active context variables to limit data required to be fetched from API
                # Note: using context is not required if there is no need or ability to limit
                # data retrieved from API.
                # listening_idx = set(self.async_contexts())
                result = await self.my_api.get_all_status()

                for device in self.all_devices:
                    if device["id"] in result:
                        status_list[device["id"]] = device | result[device["id"]]

                return status_list
        except TinxyAuthenticationException as err:
            # Raising ConfigEntryAuthFailed will cancel future updates
            # and start a config flow with SOURCE_REAUTH (async_step_reauth)
            raise ConfigEntryAuthFailed from err
        except TinxyException as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
