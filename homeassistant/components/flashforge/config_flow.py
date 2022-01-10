"""Config flow for FlashForge 3D Printer."""
import typing
from typing import Any

from ffpp import Discovery
from ffpp.Printer import Printer
import voluptuous as vol

from homeassistant import config_entries, exceptions
from homeassistant.components.network import async_get_source_ip
from homeassistant.const import CONF_IP_ADDRESS, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .const import CONF_SERIAL_NUMBER, DOMAIN

# async def _async_has_devices(hass: HomeAssistant) -> bool:
#     """Return if there are devices that can be discovered."""
# T O D O Check if there are any devices that can be discovered in the network.
#     devices = await hass.async_add_executor_job(ffpp.Printer.discover)
#     return len(devices) > 0


# config_entry_flow.register_discovery_flow(
#     DOMAIN, "FlashForge 3D Printer", _async_has_devices
# )


class FlashForgeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow."""

    VERSION = 1

    ip_addr: str
    port: int
    serial: str
    machine_type: str
    printer: Printer

    async def async_step_user(self, user_input=None):
        """Run when user trying to add component."""
        # Default values.
        errors = {}
        self.port = 8899
        self.ip_addr = None

        # Validate user data
        if user_input is not None:

            if CONF_IP_ADDRESS not in user_input:
                # Try to discover printers on network and
                # then show the confirm form.
                return await self.async_step_auto()

            # Update fields to the last state.
            self.ip_addr = user_input[CONF_IP_ADDRESS]
            self.port = user_input[CONF_PORT]

            try:
                await self._get_printer_info(self.hass, user_input)

                return self._async_create_entry()
            except CannotConnect:
                errors[CONF_IP_ADDRESS] = "cannot_connect"

        return self._async_show_form(errors=errors)

    async def async_step_auto(self) -> FlowResult:
        """Try to discover ip of printer and return a confirm form."""

        ip = None
        port = 8899
        local_ip = await async_get_source_ip(self.hass)
        discovered_printers = await Discovery.getPrinters(
            self.hass.loop,
            limit=1,
            host_ip=local_ip,
        )
        # Get the first discovered printer ip
        for _, ip_addr in discovered_printers:
            ip = ip_addr
            break

        if ip is None:
            return self.async_abort(reason="no_devices_found")

        try:
            await self._get_printer_info(
                self.hass, {CONF_IP_ADDRESS: ip, CONF_PORT: port}
            )
        except CannotConnect:
            return self.async_abort(reason="no_devices_found")

        self._set_confirm_only()
        return self.async_show_form(
            step_id="auto_confirm",
            description_placeholders={
                "machine_name": self.printer.machine_name,
                "ip_addr": ip,
            },
        )

    async def async_step_auto_confirm(
        self, _: typing.Dict[str, Any] = None
    ) -> FlowResult:
        """User confirmed to add device to Home Assistant."""
        return self._async_create_entry()

    @callback
    def _async_show_form(
        self,
        errors: typing.Dict[str, str] = None,
    ) -> FlowResult:
        """Create and show the form for user."""

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_IP_ADDRESS,
                    description={"suggested_value": self.ip_addr},
                ): str,
                vol.Optional(CONF_PORT, default=self.port): cv.port,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors or {},
        )

    async def _get_printer_info(self, hass: HomeAssistant, user_input: dict) -> None:
        """Try to get info from given ip."""

        self.ip_addr = user_input[CONF_IP_ADDRESS]
        self.port = user_input[CONF_PORT]
        self.printer = Printer(self.ip_addr, self.port)

        try:
            await self.printer.connect()
        except TimeoutError as err:
            raise CannotConnect(err) from err
        except ConnectionError as err:
            raise CannotConnect(err) from err

        if self.printer.serial is not None:
            await self.async_set_unique_id(self.printer.serial)

        self._abort_if_unique_id_configured(
            updates={CONF_IP_ADDRESS: self.ip_addr, CONF_PORT: self.port}
        )

    @callback
    def _async_create_entry(self) -> FlowResult:
        return self.async_create_entry(
            title=self.printer.machine_name,
            data={
                CONF_IP_ADDRESS: self.ip_addr,
                CONF_PORT: self.port,
                CONF_SERIAL_NUMBER: self.printer.serial,
            },
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""
