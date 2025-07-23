"""Tinxy integration coordinator."""

from datetime import timedelta
import logging
from typing import Any

import async_timeout

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.debounce import Debouncer

from .tinxycloud import TinxyAuthenticationException, TinxyException

_LOGGER = logging.getLogger(__name__)
REQUEST_REFRESH_DELAY = 0.35


class TinxyUpdateCoordinator(DataUpdateCoordinator):
    """Tinxy data update coordinator."""

    def __init__(self, hass: HomeAssistant, my_api: Any) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Tinxy",
            update_interval=timedelta(seconds=7),
            request_refresh_debouncer=Debouncer(
                hass, _LOGGER, cooldown=REQUEST_REFRESH_DELAY, immediate=False
            ),
        )
        self.hass = hass
        self.my_api = my_api
        self.all_devices = self.my_api.list_all_devices()

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            async with async_timeout.timeout(10):
                status_list = {}
                result = await self.my_api.get_all_status()

                for device in self.all_devices:
                    if device["id"] in result:
                        status_list[device["id"]] = device | result[device["id"]]

                return status_list
        except TinxyAuthenticationException as err:
            raise ConfigEntryAuthFailed from err
        except TinxyException as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
