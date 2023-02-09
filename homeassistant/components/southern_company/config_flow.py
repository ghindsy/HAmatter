"""Config flow for Southern Company integration."""
from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from southern_company_api.parser import (
    CantReachSouthernCompany,
    InvalidLogin,
    SouthernCompanyAPI,
)
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Southern Company."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            self._async_abort_entries_match({CONF_USERNAME: user_input[CONF_USERNAME]})

            sca = SouthernCompanyAPI(user_input["username"], user_input["password"])
            try:
                await sca.authenticate()
            except CantReachSouthernCompany:
                errors["base"] = "cannot_connect"
            except InvalidLogin:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title="Southern Company", data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> FlowResult:
        """Handle reauthentication."""
        return await self.async_step_reauth_confirm(entry_data)

    async def async_step_reauth_confirm(
        self, user_input: Mapping[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initiated by reauthentication."""
        errors = {}
        if user_input is not None:
            data_schema = {
                vol.Required(CONF_USERNAME, default=user_input[CONF_USERNAME]): str,
                vol.Required(CONF_PASSWORD): str,
            }

            sca = SouthernCompanyAPI(user_input["username"], user_input["password"])
            try:
                await sca.authenticate()
            except CantReachSouthernCompany:
                errors["base"] = "cannot_connect"
            except InvalidLogin:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title="Southern Company", data=user_input
                )

        return self.async_show_form(
            step_id="reauth_confirm", data_schema=data_schema, errors=errors
        )
