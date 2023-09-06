"""Config flow for the BLE Tracker."""
from __future__ import annotations

import base64
import binascii
import logging

import voluptuous as vol

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigFlow
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN
from .coordinator import async_last_service_info

_LOGGER = logging.getLogger(__name__)

CONF_IRK = "irk"


class BLEDeviceTrackerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BLE Device Tracker."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Set up by user."""
        errors: dict[str, str] = {}

        if not bluetooth.async_scanner_count(self.hass, connectable=False):
            return self.async_abort(reason="bluetooth_not_available")

        if user_input is not None:
            irk = user_input[CONF_IRK]
            if irk.startswith("irk:"):
                irk = irk[4:]

            if irk.endswith("="):
                irk_bytes = bytes(reversed(base64.b64decode(irk)))
            else:
                irk_bytes = binascii.unhexlify(irk)

            if len(irk_bytes) != 16:
                errors[CONF_IRK] = "irk_not_valid"
            elif not (service_info := async_last_service_info(self.hass, irk_bytes)):
                errors[CONF_IRK] = "irk_not_found"
            else:
                await self.async_set_unique_id(irk_bytes.hex())
                return self.async_create_entry(
                    title=service_info.name or "BLE Device Tracker",
                    data={CONF_IRK: irk_bytes.hex()},
                )

        data_schema = vol.Schema({CONF_IRK: str})
        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )
