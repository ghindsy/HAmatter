"""Config flow for Monarch Money integration."""

from __future__ import annotations

import logging
from typing import Any

from monarchmoney import LoginFailedException, MonarchMoney
from monarchmoney.monarchmoney import SESSION_FILE
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import CONF_MFA_SECRET, DOMAIN, LOGGER

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_MFA_SECRET): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user. Upon success a session will be saved
    """
    mfa_secret_key = data.get(CONF_MFA_SECRET, "")
    email = data[CONF_EMAIL]
    password = data[CONF_PASSWORD]

    # Test that we can login:
    monarch_client = MonarchMoney()
    try:
        await monarch_client.login(
            email=email,
            password=password,
            save_session=False,
            use_saved_session=False,
            mfa_secret_key=mfa_secret_key,
        )
    except LoginFailedException as exc:
        raise InvalidAuth from exc

    # monarch_client.token
    LOGGER.debug(f"Connection successful - saving session to file {SESSION_FILE}")

    # Return info that you want to store in the config entry.
    return {"title": "Monarch Money", CONF_TOKEN: monarch_client.token}


class MonarchMoneyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Monarch Money."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=info["title"], data={CONF_TOKEN: info[CONF_TOKEN]}
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
