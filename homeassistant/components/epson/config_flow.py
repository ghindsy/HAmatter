"""Config flow for epson integration."""
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT

from . import validate_projector
from .const import DOMAIN
from .exceptions import CannotConnect

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_NAME, default=DOMAIN): str,
        vol.Required(CONF_PORT, default=80): int,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for epson."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_import(self, import_config):
        """Import a config entry from configuration.yaml."""
        return await self.async_step_user(import_config)

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            if self.host_already_configured(user_input[CONF_HOST]):
                return self.async_abort(reason="already_configured")
            try:
                await validate_projector(
                    self.hass, user_input[CONF_HOST], user_input[CONF_PORT]
                )
                name = user_input.pop(CONF_NAME)
                await self.async_set_unique_id(name)
                return self.async_create_entry(title=name, data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    def host_already_configured(self, host):
        """See if we already have a entry matching user input configured."""
        existing_hosts = {
            entry.data[CONF_HOST] for entry in self._async_current_entries()
        }
        return host in existing_hosts
