"""Config flow for Smappee."""
import logging
import socket

from requests.exceptions import ConnectionError, ConnectTimeout
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_IP_ADDRESS
from homeassistant.helpers import config_entry_oauth2_flow

from . import api
from .const import CONF_HOSTNAME, CONF_SERIALNUMBER, DOMAIN, ENV_CLOUD, ENV_LOCAL

_LOGGER = logging.getLogger(__name__)


class SmappeeFlowHandler(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN
):
    """Config Smappee config flow."""

    DOMAIN = DOMAIN
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    @property
    def logger(self) -> logging.Logger:
        """Return logger."""
        return logging.getLogger(__name__)

    async def async_step_zeroconf(self, user_input):
        """Handle zeroconf discovery."""
        if user_input is None:
            return self.async_abort(reason="connection_error")

        if not user_input[CONF_HOSTNAME].startswith("Smappee1"):
            # We currently only support Energy and Solar models (legacy)
            return self.async_abort(reason="invalid_mdns")

        self.context.update(
            {
                CONF_IP_ADDRESS: user_input["host"],
                CONF_SERIALNUMBER: user_input[CONF_HOSTNAME]
                .replace(".local.", "")
                .replace("Smappee", ""),
            }
        )

        # Prepare configuration flow
        return await self.async_step_zeroconf_initiate(user_input, True)

    async def async_step_zeroconf_initiate(self, user_input=None, prepare=False):
        """Handle a flow initiated by zeroconf."""

        # Prepare zeroconf discovery flow
        if user_input is None and not prepare:
            return self._show_zeroconf_confirm_dialog()

        user_input[CONF_IP_ADDRESS] = self.context.get(CONF_IP_ADDRESS)
        user_input[CONF_SERIALNUMBER] = self.context.get(CONF_SERIALNUMBER)

        if user_input.get(CONF_IP_ADDRESS) is not None or not prepare:
            smappee_api = api.api.SmappeeLocalApi(ip=user_input[CONF_IP_ADDRESS])
            try:
                await self.hass.async_add_executor_job(smappee_api.logon)
            except (socket.gaierror, socket.timeout, ConnectTimeout, ConnectionError):
                return self.async_abort(reason="connection_error")

        # Check if already configured
        await self.async_set_unique_id(f"Smappee{user_input[CONF_SERIALNUMBER]}")
        self._abort_if_unique_id_configured()

        if prepare:
            return await self.async_step_zeroconf_confirm()

        return self.async_create_entry(
            title=f"Smappee{user_input[CONF_SERIALNUMBER]}",
            data={
                CONF_IP_ADDRESS: user_input[CONF_IP_ADDRESS],
                CONF_SERIALNUMBER: user_input[CONF_SERIALNUMBER],
            },
        )

    async def async_step_zeroconf_confirm(self, user_input=None):
        """Confirm zeroconf flow."""
        return await self.async_step_zeroconf_initiate(user_input)

    def _show_zeroconf_confirm_dialog(self, errors=None):
        """Show the confirm dialog to the user."""
        serialnumber = self.context.get(CONF_SERIALNUMBER)
        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders={"serialnumber": serialnumber},
            errors=errors or {},
        )

    async def async_step_user(self, user_input=None):
        """Handle a flow initiated by the user."""
        return await self._handle_config_flow(user_input)

    async def _handle_config_flow(self, user_input=None, prepare=False):
        """Config flow handler for Smappee."""

        # Show LOCAL/CLOUD option or prepare zeroconf discovery flow
        if user_input is None and not prepare:
            # Show environment form with CLOUD or LOCAL option
            return self._show_environment_setup_form()

        # Environment chosen, request additional host information for LOCAL or OAuth2 flow for CLOUD
        if user_input is not None and "environment" in user_input:
            if user_input["environment"] == ENV_LOCAL:
                self.context.update({"environment": ENV_LOCAL})
                return self._show_host_setup_form()

            # Use configuration.yaml CLOUD setup
            self.context.update({"environment": ENV_CLOUD})
            return await self.async_step_pick_implementation()

        user_input[CONF_IP_ADDRESS] = user_input["host"]

        if user_input.get(CONF_IP_ADDRESS) is not None or not prepare:
            smappee_api = api.api.SmappeeLocalApi(ip=user_input[CONF_IP_ADDRESS])
            try:
                await self.hass.async_add_executor_job(smappee_api.logon)

                # In a LOCAL setup we still need to resolve the host to serialnumber
                advanced_config = await self.hass.async_add_executor_job(
                    smappee_api.load_advanced_config
                )
                serialnumber = None
                for config_item in advanced_config:
                    if config_item["key"] == "mdnsHostName":
                        serialnumber = config_item["value"]

                if serialnumber is None or not serialnumber.startswith("Smappee1"):
                    # We currently only support Energy and Solar models (legacy)
                    return self.async_abort(reason="invalid_mdns")
                user_input[CONF_SERIALNUMBER] = serialnumber.replace("Smappee", "")
            except (socket.gaierror, socket.timeout, ConnectTimeout, ConnectionError):
                return self.async_abort(reason="connection_error")

        # Check if already configured
        await self.async_set_unique_id(f"Smappee{user_input[CONF_SERIALNUMBER]}")
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=f"Smappee{user_input[CONF_SERIALNUMBER]}",
            data={
                CONF_IP_ADDRESS: user_input[CONF_IP_ADDRESS],
                CONF_SERIALNUMBER: user_input[CONF_SERIALNUMBER],
            },
        )

    def _show_environment_setup_form(self, errors=None):
        """Show the environment form to the user."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("environment", default=ENV_CLOUD): vol.In(
                        [ENV_CLOUD, ENV_LOCAL]
                    )
                }
            ),
            errors=errors or {},
        )

    def _show_host_setup_form(self, errors=None):
        """Show the host form to the user."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_HOST): str}),
            errors=errors or {},
        )
