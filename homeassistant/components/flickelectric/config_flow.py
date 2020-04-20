"""Config Flow for Flick Electric integration."""
from asyncio import TimeoutError
import logging

import async_timeout
from pyflick.authentication import AuthException, SimpleFlickAuth
from pyflick.const import DEFAULT_CLIENT_ID, DEFAULT_CLIENT_SECRET
import voluptuous as vol

from homeassistant import config_entries, data_entry_flow
from homeassistant.const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_PASSWORD,
    CONF_USERNAME,
)
from homeassistant.helpers import aiohttp_client

from .const import DOMAIN  # pylint: disable=unused-import

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_CLIENT_ID): str,
        vol.Optional(CONF_CLIENT_SECRET): str,
    }
)


class FlickConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Flick config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def _validate_input(self, user_input):
        auth = SimpleFlickAuth(
            username=user_input[CONF_USERNAME],
            password=user_input[CONF_PASSWORD],
            websession=aiohttp_client.async_get_clientsession(self.hass),
            client_id=user_input.get(CONF_CLIENT_ID, DEFAULT_CLIENT_ID),
            client_secret=user_input.get(CONF_CLIENT_SECRET, DEFAULT_CLIENT_SECRET),
        )

        with async_timeout.timeout(60):
            token = await auth.async_get_access_token()

            return token is not None

    async def async_step_user(self, user_input):
        """Handle gathering login info."""
        errors = {}
        if user_input is not None:
            try:
                await self._validate_input(user_input)

                await self.async_set_unique_id(
                    f"flickelectric_{user_input[CONF_USERNAME]}"
                )
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Flick Electric: {user_input[CONF_USERNAME]}",
                    data=user_input,
                )
            except TimeoutError:
                errors["base"] = "cannot_connect"
            except AuthException:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )
