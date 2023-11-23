"""Config flow for Netgear LTE integration."""
from __future__ import annotations

from typing import Any

from aiohttp.cookiejar import CookieJar
from eternalegypt import Error, Modem
from eternalegypt.eternalegypt import Information
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import DEFAULT_HOST, DOMAIN, MANUFACTURER


class NetgearLTEFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Netgear LTE."""

    async def async_step_import(self, config: dict[str, Any]) -> FlowResult:
        """Import a configuration from config.yaml."""
        return await self.async_step_user(
            user_input={
                CONF_HOST: config[CONF_HOST],
                CONF_PASSWORD: config[CONF_PASSWORD],
            }
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initiated by the user."""
        errors = {}

        if user_input:
            host = user_input[CONF_HOST]
            password = user_input[CONF_PASSWORD]

            info, error = await self._async_validate_input(host, password)
            if info:
                await self.async_set_unique_id(info.serial_number)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"{MANUFACTURER} {info.items['general.devicename']}",
                    data={CONF_HOST: host, CONF_PASSWORD: password},
                )
            if error:
                errors["base"] = error

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(CONF_HOST): str,
                        vol.Required(CONF_PASSWORD): str,
                    }
                ),
                user_input or {CONF_HOST: DEFAULT_HOST},
            ),
            errors=errors,
        )

    async def _async_validate_input(
        self, host: str, password: str
    ) -> tuple[Information, None] | tuple[None, str]:
        """Validate login credentials."""
        websession = async_create_clientsession(
            self.hass, cookie_jar=CookieJar(unsafe=True)
        )

        modem = Modem(
            hostname=host,
            password=password,
            websession=websession,
        )
        try:
            await modem.login()
        except Error:
            return None, "cannot_connect"
        except Exception:  # pylint: disable=broad-except
            return None, "unknown"
        return await modem.information(), None
