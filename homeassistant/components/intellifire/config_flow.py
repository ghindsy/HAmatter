"""Config flow for IntelliFire integration."""
from __future__ import annotations

from typing import Any

from aiohttp import ClientConnectionError
from intellifire4py import AsyncUDPFireplaceFinder, IntellifireAsync
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, LOGGER

STEP_USER_DATA_SCHEMA = vol.Schema({vol.Required(CONF_HOST): str})

MANUAL_ENTRY_STRING = "IP Address"  # Simplified so it does not have to be translated


async def validate_host_input(host: str) -> str:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    api = IntellifireAsync(host)
    await api.poll()
    ret = api.data.serial
    LOGGER.debug("Found a fireplace: %s", ret)
    # Return the serial number which will be used to calculate a unique ID for the device/sensors
    return ret


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for IntelliFire."""

    VERSION = 1

    def __init__(self):
        """Initialize the Config Flow Handler."""
        self._config_context = {}
        self._not_configured_hosts: list[str] = []

    async def _find_fireplaces(self):
        """Perform UDP discovery."""
        fireplace_finder = AsyncUDPFireplaceFinder()
        discovered_hosts = await fireplace_finder.search_fireplace(timeout=1)
        configured_hosts = {
            entry.data[CONF_HOST]
            for entry in self._async_current_entries(include_ignore=False)
            if CONF_HOST in entry.data  # CONF_HOST will be missing for ignored entries
        }

        self._not_configured_hosts = [
            ip for ip in discovered_hosts if ip not in configured_hosts
        ]
        LOGGER.debug("Discovered Hosts: %s", str(discovered_hosts))
        LOGGER.debug("Configured Hosts: %s", str(configured_hosts))
        LOGGER.debug("Not Configured Hosts: %s", str(self._not_configured_hosts))

    async def _async_validate_and_create_entry(self, host: str) -> FlowResult:
        """Validate and create the entry."""
        self._async_abort_entries_match({CONF_HOST: host})
        serial = await validate_host_input(host)
        await self.async_set_unique_id(serial)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})
        return self.async_create_entry(
            title=f"Fireplace {serial}",
            data={CONF_HOST: host},
        )

    async def async_step_manual_device_entry(self, user_input=None):
        """Handle manual input of local IP configuration."""
        errors = {}
        host = user_input.get(CONF_HOST) if user_input else None
        if user_input is not None:
            try:
                return await self._async_validate_and_create_entry(host)
            except (ConnectionError, ClientConnectionError):
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="manual_device_entry",
            errors=errors,
            data_schema=vol.Schema({vol.Required(CONF_HOST, default=host): str}),
        )

    async def async_step_pick_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Pick which device to configure."""
        errors = {}

        if user_input is not None:
            if user_input[CONF_HOST] == MANUAL_ENTRY_STRING:
                return await self.async_step_manual_device_entry()

            try:
                return await self._async_validate_and_create_entry(
                    user_input[CONF_HOST]
                )
            except (ConnectionError, ClientConnectionError):
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="pick_device",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): vol.In(
                        self._not_configured_hosts + [MANUAL_ENTRY_STRING]
                    )
                }
            ),
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Start the user flow."""

        # Launch fireplaces discovery
        await self._find_fireplaces()

        if self._not_configured_hosts:
            LOGGER.debug("Running Step: pick_device")
            return await self.async_step_pick_device()
        LOGGER.debug("Running Step: manual_device_entry")
        return await self.async_step_manual_device_entry()
