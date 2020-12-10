"""Config flow for Niu integration."""
import logging

import voluptuous as vol
from voluptuous.schema_builder import Required

from homeassistant import config_entries, core, exceptions

from .const import DOMAIN  # pylint:disable=unused-import

from niu import NiuCloud
from niu import NiuAPIException, NiuNetException, NiuServerException

_LOGGER = logging.getLogger(__name__)

# TODO adjust the data schema to the data that you need
STEP_USER_DATA_SCHEMA = vol.Schema(
    {vol.Required("username"): str, vol.Required("password"): str}
)


async def validate_input(hass: core.HomeAssistant, data):
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    try:
        # Create new object with user data
        hub = NiuCloud(
            username=data["username"],
            password=data["password"],
            token=None,
            lang="en-US",
        )
        # Check if this action have given us a correct auth token
        if not await hub.connect():
            _LOGGER.error("No authentication token found")
            raise InvalidAuth

    except NiuAPIException as ex:
        _LOGGER.error("Error while authenticating with Niu API: %s", ex)
        raise InvalidAuth
    except NiuServerException as ex:
        _LOGGER.error("Error while making Niu API request: %s", ex)
        raise InvalidAuth
    except NiuNetException as ex:
        _LOGGER.error("Could not connect with Niu API: %s", ex)
        raise CannotConnect

    # Return info that you want to store in the config entry.
    return {"title": data["username"]}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Niu."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

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


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""
