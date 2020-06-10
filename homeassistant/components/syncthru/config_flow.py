"""Config flow for Samsung SyncThru."""

import re
from urllib.parse import urlparse

from pysyncthru import SyncThru
from url_normalize import url_normalize
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import ssdp
from homeassistant.const import CONF_NAME, CONF_URL
from homeassistant.helpers import aiohttp_client

# pylint: disable=unused-import # for DOMAIN https://github.com/PyCQA/pylint/issues/3202
from .const import DEFAULT_MODEL, DEFAULT_NAME_TEMPLATE, DOMAIN


class SyncThruConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Samsung SyncThru config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Handle user initiated flow."""
        if user_input is None:
            return await self._async_show_form(step_id="user")
        return await self._async_check_and_create("user", user_input)

    async def async_step_import(self, user_input=None):
        """Handle import initiated flow."""
        return await self.async_step_user(user_input=user_input)

    async def async_step_ssdp(self, discovery_info):
        """Handle SSDP initiated flow."""
        await self.async_set_unique_id(discovery_info[ssdp.ATTR_UPNP_UDN])
        self._abort_if_unique_id_configured()

        url = discovery_info.get(
            ssdp.ATTR_UPNP_PRESENTATION_URL,
            f"http://{urlparse(discovery_info[ssdp.ATTR_SSDP_LOCATION]).hostname}/",
        )
        if any(x.data[CONF_URL] == url for x in self._async_current_entries()):
            return self.async_abort(reason="already_configured")

        name = discovery_info.get(ssdp.ATTR_UPNP_FRIENDLY_NAME)
        if name:
            # Remove trailing " (ip)" if present for consistency with user driven config
            name = re.sub(r"\s+\([\d.]+\)\s*$", "", name)

        self.context.update(
            {CONF_URL: url, CONF_NAME: name, "title_placeholders": {CONF_NAME: name}}
        )
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input=None):
        """Handle discovery confirmation by user."""
        if user_input is not None:
            return await self._async_check_and_create("confirm", user_input)

        return await self._async_show_form(
            step_id="confirm",
            user_input={
                CONF_URL: self.context[CONF_URL],
                CONF_NAME: self.context[CONF_NAME],
            },
        )

    async def _async_show_form(self, step_id, user_input=None, errors=None):
        """Show our form."""
        if user_input is None:
            user_input = {}
        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_URL, default=user_input.get(CONF_URL, "")): str,
                    vol.Optional(CONF_NAME, default=user_input.get(CONF_NAME, "")): str,
                }
            ),
            errors=errors or {},
        )

    async def _async_check_and_create(self, step_id, user_input):
        """Validate input, proceed to create."""
        user_input[CONF_URL] = url_normalize(
            user_input[CONF_URL], default_scheme="http"
        )
        if "://" not in user_input[CONF_URL]:
            return await self._async_show_form(
                step_id=step_id, user_input=user_input, errors={CONF_URL: "invalid_url"}
            )

        await self.async_set_unique_id(user_input[CONF_URL])
        self._abort_if_unique_id_configured()

        if any(
            x.data[CONF_URL] == user_input[CONF_URL]
            for x in self._async_current_entries()
        ):
            return self.async_abort(reason="already_configured")

        session = aiohttp_client.async_get_clientsession(self.hass)
        printer = SyncThru(user_input[CONF_URL], session)
        errors = {}
        try:
            await printer.update()
            if not user_input.get(CONF_NAME):
                user_input[CONF_NAME] = DEFAULT_NAME_TEMPLATE.format(
                    printer.model() or DEFAULT_MODEL
                )
        except ValueError:
            errors[CONF_URL] = "syncthru_not_supported"
        else:
            if printer.is_unknown_state():
                errors[CONF_URL] = "unknown_state"

        if errors:
            return await self._async_show_form(
                step_id=step_id, user_input=user_input, errors=errors
            )

        return self.async_create_entry(
            title=user_input.get(CONF_NAME), data=user_input,
        )
