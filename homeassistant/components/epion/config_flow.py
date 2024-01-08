"""Config flow for Epion."""
from __future__ import annotations

import logging
from typing import Any

from epion import Epion
from requests.exceptions import ConnectTimeout, HTTPError
from voluptuous import Required, Schema

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_API_KEY
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class EpionConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Epion."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initiated by the user."""
        errors = {}
        if user_input is not None:
            try:
                key_valid = await self.hass.async_add_executor_job(
                    self._check_api_key, user_input[CONF_API_KEY]
                )
                if key_valid:
                    return self.async_create_entry(
                        title="Epion integration",
                        data={CONF_API_KEY: user_input[CONF_API_KEY]},
                    )
                else:
                    errors["base"] = "invalid_api_key"
            except (HTTPError, ConnectTimeout, KeyError):
                _LOGGER.error("Unexpected problem when configuring Epion API")
                errors["base"] = "could_not_connect"
        else:
            user_input = {}
            user_input[CONF_API_KEY] = ""

        return self.async_show_form(
            step_id="user",
            data_schema=Schema(
                {
                    Required(CONF_API_KEY, default=user_input[CONF_API_KEY]): str,
                }
            ),
            errors=errors,
        )

    def _check_api_key(self, api_key: str) -> bool:
        """Try to connect and see if the API key is valid."""
        api = Epion(api_key)
        try:
            return len(api.get_current()["devices"]) > 0
        except HTTPError as ex:
            if ex.response is not None:
                if ex.response.status_code == 401:
                    return False
            raise ex
        except Exception as ex:
            raise ex
