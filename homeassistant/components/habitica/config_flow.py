"""Config flow for habitica integration."""

from __future__ import annotations

from http import HTTPStatus
import logging
from typing import Any

from aiohttp import ClientResponseError
from habitipy.aio import HabitipyAsync
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import (
    CONF_API_KEY,
    CONF_PASSWORD,
    CONF_URL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import DOMAIN as HOMEASSISTANT_DOMAIN
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.issue_registry import IssueSeverity, async_create_issue

from .const import CONF_API_USER, DEFAULT_URL, DOMAIN

STEP_ADVANCED_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_USER): str,
        vol.Required(CONF_API_KEY): str,
        vol.Optional(CONF_URL, default=DEFAULT_URL): str,
        vol.Required(CONF_VERIFY_SSL, default=True): bool,
    }
)

STEP_LOGIN_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: HomeAssistant, data: dict[str, str]) -> dict[str, str]:
    """Validate the user input allows us to connect."""

    websession = async_get_clientsession(hass)
    api = await hass.async_add_executor_job(
        HabitipyAsync,
        {
            "login": data[CONF_API_USER],
            "password": data[CONF_API_KEY],
            "url": data[CONF_URL] or DEFAULT_URL,
        },
    )
    try:
        await api.user.get(session=websession)
        return {
            "title": f"{data.get('name', 'Default username')}",
            CONF_API_USER: data[CONF_API_USER],
        }
    except ClientResponseError as ex:
        if ex.status == HTTPStatus.UNAUTHORIZED:
            raise InvalidAuth from ex
        raise CannotConnect from ex


class HabiticaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for habitica."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""

        return self.async_show_menu(
            step_id="user",
            menu_options=["login", "advanced"],
        )

    async def async_step_login(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Config flow with username/password.

        Simplified configuration setup that retrieves API credentials
        from Habitica.com by authenticating with login and password.
        """
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                session = async_get_clientsession(self.hass)
                api = HabitipyAsync(
                    conf={
                        "login": "",
                        "password": "",
                        "url": DEFAULT_URL,
                    }
                )
                login_response = await api.user.auth.local.login.post(
                    session=session,
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                )

            except ClientResponseError as ex:
                if ex.status == HTTPStatus.UNAUTHORIZED:
                    errors["base"] = "invalid_auth"
                else:
                    errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(login_response["id"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=login_response["username"],
                    data={
                        CONF_API_USER: login_response["id"],
                        CONF_API_KEY: login_response["apiToken"],
                        CONF_USERNAME: login_response["username"],
                        CONF_URL: DEFAULT_URL,
                        CONF_VERIFY_SSL: True,
                    },
                )

        return self.async_show_form(
            step_id="login",
            data_schema=self.add_suggested_values_to_schema(
                data_schema=STEP_LOGIN_DATA_SCHEMA, suggested_values=user_input
            ),
            errors=errors,
        )

    async def async_step_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Advanced configuration with User Id and API Token.

        Advanced configuration allows connecting to Habitica instances
        hosted on different domains or to self-hosted instances.
        """
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                session = async_get_clientsession(
                    self.hass, verify_ssl=user_input.get(CONF_VERIFY_SSL, True)
                )
                api = HabitipyAsync(
                    conf={
                        "login": user_input[CONF_API_USER],
                        "password": user_input[CONF_API_KEY],
                        "url": user_input.get(CONF_URL, DEFAULT_URL),
                    }
                )
                api_response = await api.user.get(
                    session=session,
                    userFields="auth",
                )
            except ClientResponseError as ex:
                if ex.status == HTTPStatus.UNAUTHORIZED:
                    errors["base"] = "invalid_auth"
                else:
                    errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_input[CONF_API_USER])
                self._abort_if_unique_id_configured()
                user_input[CONF_USERNAME] = api_response["auth"]["local"]["username"]
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME], data=user_input
                )

        return self.async_show_form(
            step_id="advanced",
            data_schema=self.add_suggested_values_to_schema(
                data_schema=STEP_ADVANCED_DATA_SCHEMA, suggested_values=user_input
            ),
            errors=errors,
        )

    async def async_step_import(self, import_data) -> ConfigFlowResult:
        """Import habitica config from configuration.yaml."""

        async_create_issue(
            self.hass,
            HOMEASSISTANT_DOMAIN,
            f"deprecated_yaml_{DOMAIN}",
            is_fixable=False,
            breaks_in_ha_version="2024.11.0",
            severity=IssueSeverity.WARNING,
            translation_key="deprecated_yaml",
            translation_placeholders={
                "domain": DOMAIN,
                "integration_title": "Habitica",
            },
        )
        return await self.async_step_advanced(import_data)
