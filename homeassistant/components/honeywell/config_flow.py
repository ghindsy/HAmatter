"""Config flow to configure the honeywell integration."""
import somecomfort
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from .const import DOMAIN


class HoneywellConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a honeywell config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Create config entry. Show the setup form to the user."""
        errors = {}

        if user_input is not None:
            valid = await self.is_valid(user_input["username"], user_input["password"])
            if valid:
                return self.async_create_entry(
                    title=DOMAIN,
                    data=user_input,
                )

            errors["base"] = "auth_error"

        data_schema = {
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
        }
        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(data_schema), errors=errors
        )

    async def is_valid(self, username, password) -> bool:
        """Check if login credentials are valid."""
        try:
            await self.hass.async_add_executor_job(
                somecomfort.SomeComfort, username, password
            )
            return True
        except somecomfort.SomeComfortError:
            return False

    async def async_step_import(self, import_data):
        """Import entry from configuration.yaml."""
        return await self.async_step_user(import_data)
