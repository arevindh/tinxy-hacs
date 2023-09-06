"""Config flow for Tinxy integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_API_KEY, DOMAIN, TINXY_BACKEND
from .tinxycloud import TinxyCloud, TinxyHostConfiguration

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
    }
)


class TinxyHub:
    def __init__(self, host: str) -> bool:
        """Initialize."""

        self.host = host

    async def authenticate(self, api_key: str, web_session) -> bool:
        """Test if we can authenticate with the host."""

        host_config = TinxyHostConfiguration(
            api_token=api_key, api_url=self.host)
        api = TinxyCloud(host_config=host_config, web_session=web_session)
        await api.sync_devices()
        return True


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # TODO validate the data can be used to set up a connection.

    # If your PyPI package is not built with async, pass your methods
    # to the executor:
    # await hass.async_add_executor_job(
    #     your_validate_func, data["username"], data["password"]
    # )
    web_session = async_get_clientsession(hass)
    hub = TinxyHub(TINXY_BACKEND)

    if not await hub.authenticate(data[CONF_API_KEY], web_session):
        raise InvalidAuth

    # If you cannot connect:
    # throw CannotConnect
    # If the authentication is wrong:
    # InvalidAuth

    # Return info that you want to store in the config entry.
    return {"title": "Tinxy.in"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tinxy."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


async def async_step_zeroconf(self, zeroconf_info):
    """Handle zeroconf discovery."""
    # Extract info from zeroconf_info and make sure it starts with "tinxy"
    host = zeroconf_info[CONF_HOST]
    name = zeroconf_info.get(CONF_NAME, "")

    if not name.startswith("tinxy"):
        return self.async_abort(reason="not_tinxy_device")

    # You can now proceed with creating a config entry or aborting
    await self.async_set_unique_id(name)
    self._abort_if_unique_id_configured()

    return self.async_create_entry(
        title=name,
        data={
            "host": host,
            # Add any other data you might need
        },
    )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
