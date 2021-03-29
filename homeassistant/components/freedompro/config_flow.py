"""Config flow to configure Freedompro."""
from pyfreedompro import get_list
import voluptuous as vol

from homeassistant import config_entries, core, exceptions
from homeassistant.const import CONF_API_KEY
from homeassistant.helpers import aiohttp_client

from .const import DOMAIN  # pylint:disable=unused-import

STEP_USER_DATA_SCHEMA = vol.Schema({vol.Required(CONF_API_KEY): str})


class Hub:
    """Freedompro Hub class."""

    def __init__(self, hass, api_key):
        """Freedompro Hub class init."""
        self._hass = hass
        self._api_key = api_key

    async def authenticate(self) -> bool:
        """Freedompro Hub class authenticate."""
        result = await get_list(
            aiohttp_client.async_get_clientsession(self._hass), self._api_key
        )
        return result


async def validate_input(hass: core.HomeAssistant, data):
    """Validate api key."""
    hub = Hub(hass, data["api_key"])
    result = await hub.authenticate()
    if result["state"] is False:
        if result["code"] == -201:
            raise InvalidAuth
        if result["code"] == -200:
            raise CannotConnect
    return {"title": "Freedompro"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Show the setup form to the user."""
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
        else:
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""
