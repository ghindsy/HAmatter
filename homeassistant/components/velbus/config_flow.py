"""Config flow for the Velbus platform."""
from __future__ import annotations

from typing import Any

import velbusaio
from velbusaio.exceptions import VelbusConnectionFailed
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import usb
from homeassistant.const import CONF_NAME, CONF_PORT
from homeassistant.data_entry_flow import FlowResult
from homeassistant.util import slugify

from .const import DOMAIN


class VelbusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the velbus config flow."""
        self._errors: dict[str, str] = {}
        self._device: str = ""
        self._title: str = ""

    def _create_device(self, name: str, prt: str) -> FlowResult:
        """Create an entry async."""
        return self.async_create_entry(title=name, data={CONF_PORT: prt})

    async def _test_connection(self, prt: str) -> bool:
        """Try to connect to the velbus with the port specified."""
        try:
            controller = velbusaio.controller.Velbus(prt)
            await controller.connect(True)
            await controller.stop()
        except VelbusConnectionFailed:
            self._errors[CONF_PORT] = "cannot_connect"
            return False
        return True

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step when user initializes a integration."""
        self._errors = {}
        if user_input is not None:
            name = slugify(user_input[CONF_NAME])
            prt = user_input[CONF_PORT]
            self._async_abort_entries_match({CONF_PORT: prt})
            if await self._test_connection(prt):
                return self._create_device(name, prt)
        else:
            user_input = {}
            user_input[CONF_NAME] = ""
            user_input[CONF_PORT] = ""

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=user_input[CONF_NAME]): str,
                    vol.Required(CONF_PORT, default=user_input[CONF_PORT]): str,
                }
            ),
            errors=self._errors,
        )

    async def async_step_usb(self, discovery_info: usb.UsbServiceInfo) -> FlowResult:
        """Handle USB Discovery."""
        await self.async_set_unique_id(usb.generate_unique_id(discovery_info))
        # check if this device is not already configured
        self._async_abort_entries_match({CONF_PORT: discovery_info.device})
        # check if we can make a valid velbus connection
        if not await self._test_connection(discovery_info.device):
            return self.async_abort(reason="cannot_connect")
        # store the data for the config step
        self._device = discovery_info.device
        self._title = "Velbus USB"
        # call the config step
        self._set_confirm_only()
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle Discovery confirmation."""
        if user_input is not None:
            return self._create_device(self._title, self._device)

        return self.async_show_form(
            step_id="discovery_confirm",
            description_placeholders={CONF_NAME: self._title},
        )
