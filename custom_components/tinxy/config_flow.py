"""
Config flow for the Tinxy Home Assistant integration.

This module handles the configuration flow for the Tinxy custom component,
including user authentication and validation.
"""

from __future__ import annotations
import logging
from typing import Any, Dict, Optional
from dataclasses import dataclass

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, TINXY_BACKEND
from .tinxycloud import TinxyCloud, TinxyHostConfiguration

# Module-level logger
LOGGER = logging.getLogger(__name__)

# Constants
STEP_ID_USER = "user"
TITLE = "Tinxy"

# Data schema for the user step
STEP_USER_DATA_SCHEMA = vol.Schema({vol.Required(CONF_API_KEY): str})

def _log_and_raise(error: Exception, message: str, exc_type: type) -> None:
    """
    Log the error and raise the specified exception type.
    Args:
        error: The original exception.
        message: The log message.
        exc_type: The exception class to raise.
    """
    LOGGER.error(message + ": %s", error)
    raise exc_type from error

async def validate_user_input(
    hass: HomeAssistant, user_data: Dict[str, Any]
) -> Dict[str, str]:
    """
    Validate user input and attempt to authenticate with Tinxy API.

    Args:
        hass: HomeAssistant instance.
        user_data: Dictionary containing user-provided configuration.

    Returns:
        Dictionary with integration title if successful.

    Raises:
        InvalidAuth: If authentication fails.
        CannotConnect: If unable to connect to the API.
    """
    web_session = async_get_clientsession(hass)
    host_config = TinxyHostConfiguration(
        api_token=user_data[CONF_API_KEY],
        api_url=TINXY_BACKEND,
    )
    api = TinxyCloud(host_config=host_config, web_session=web_session)
    try:
        await api.sync_devices()
    except Exception as err:
        # Log and raise InvalidAuth for any authentication or connection error
        _log_and_raise(err, "Failed to authenticate with Tinxy API", InvalidAuth)
    return {"title": TITLE}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """
    Handle the configuration flow for the Tinxy integration.

    This class manages the user interaction and validation steps required
    to set up the Tinxy integration in Home Assistant.
    """
    VERSION: int = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """
        Handle the initial user step of the config flow.

        Args:
            user_input: Optional dictionary of user input from the form.

        Returns:
            FlowResult: The result of the flow step, either showing the form or creating the entry.
        """
        errors: Dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_user_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
                LOGGER.warning("Cannot connect to Tinxy API.")
            except InvalidAuth:
                errors["base"] = "invalid_auth"
                LOGGER.warning("Invalid authentication for Tinxy API.")
            except Exception as exc:
                LOGGER.exception("Unexpected exception during Tinxy config flow: %s", exc)
                errors["base"] = "unknown"
            else:
                LOGGER.info("Tinxy integration setup successful.")
                return self.async_create_entry(title=info["title"], data=user_input)

        # Show the form again if there are errors or no input
        return self.async_show_form(
            step_id=STEP_ID_USER,
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """
    Error to indicate we cannot connect to the Tinxy API.
    """
    pass


class InvalidAuth(HomeAssistantError):
    """
    Error to indicate invalid authentication for Tinxy API.
    """
    pass
