"""Config flow for the dwd_weather_warnings integration."""

from __future__ import annotations

from typing import Any

from dwdwfsapi import DwdWeatherWarningsAPI
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import CONF_REGION_IDENTIFIER, CONF_REGION_NAME, DOMAIN, LOGGER


class DwdWeatherWarningsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for the dwd_weather_warnings integration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict = {}

        if user_input is not None:
            region_identifier = user_input[CONF_REGION_IDENTIFIER]

            # Validate region identifier using the API
            if not await self.hass.async_add_executor_job(
                DwdWeatherWarningsAPI, region_identifier
            ):
                errors["base"] = "invalid_identifier"

            if not errors:
                # Set the unique ID for this config entry.
                await self.async_set_unique_id(region_identifier)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(title=region_identifier, data=user_input)

        return self.async_show_form(
            step_id="user",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_REGION_IDENTIFIER): cv.string,
                }
            ),
        )

    async def async_step_import(self, import_config: dict[str, Any]) -> FlowResult:
        """Import a config entry from configuration.yaml."""
        LOGGER.debug(
            "Starting import of sensor from configuration.yaml - %s", import_config
        )

        # Extract the necessary data for the setup.
        region_identifier = import_config[CONF_REGION_NAME]
        name = import_config.get(CONF_NAME, region_identifier)

        # Set the unique ID for this imported entry.
        await self.async_set_unique_id(region_identifier)
        self._abort_if_unique_id_configured()

        # Validate region identifier using the API
        if not await self.hass.async_add_executor_job(
            DwdWeatherWarningsAPI, region_identifier
        ):
            return self.async_abort(reason="invalid_identifier")

        return self.async_create_entry(
            title=name, data={CONF_REGION_IDENTIFIER: region_identifier}
        )
