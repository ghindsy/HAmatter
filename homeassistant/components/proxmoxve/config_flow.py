"""Config flow for Proxmox VE integration."""

from __future__ import annotations

from typing import Any

from proxmoxer import AuthenticationError, ProxmoxAPI
import requests.exceptions
from requests.exceptions import ConnectTimeout, SSLError
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from . import ProxmoxClient
from .const import (
    _LOGGER,
    CONF_CONTAINERS,
    CONF_NODE,
    CONF_REALM,
    CONF_VMS,
    DEFAULT_PORT,
    DEFAULT_REALM,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_NODE, default="pve"): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Optional(CONF_REALM, default=DEFAULT_REALM): cv.string,
        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): cv.boolean,
    }
)


async def validate_input(
    hass: HomeAssistant, data: dict[str, Any]
) -> ProxmoxClient | None:
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """

    def build_client() -> ProxmoxAPI:
        try:
            proxmox_client = ProxmoxClient(
                host=data[CONF_HOST],
                port=data[CONF_PORT],
                user=data[CONF_USERNAME],
                realm=data[CONF_REALM],
                password=data[CONF_PASSWORD],
                verify_ssl=data[CONF_VERIFY_SSL],
            )
            proxmox_client.build_client()
        except AuthenticationError as err:
            _LOGGER.warning(
                "Invalid credentials for proxmox instance %s:%d",
                data[CONF_HOST],
                data[CONF_PORT],
            )
            raise InvalidAuth from err
        except SSLError as err:
            _LOGGER.error(
                (
                    "Unable to verify proxmox server SSL. "
                    'Try using "verify_ssl: false" for proxmox instance %s:%d'
                ),
                data[CONF_HOST],
                data[CONF_PORT],
            )
            raise SSLException from err
        except ConnectTimeout as err:
            _LOGGER.warning(
                "Connection to host %s timed out during setup", data[CONF_HOST]
            )
            raise ConnectTimeout from err
        except requests.exceptions.ConnectionError as err:
            _LOGGER.warning("Host %s is not reachable", data[CONF_HOST])
            raise CannotConnect from err
        return proxmox_client.get_api_client()

    return await hass.async_add_executor_job(build_client)


class ProxmoxVEConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Proxmox VE."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=DATA_SCHEMA, errors=errors
            )

        try:
            proxmox = await validate_input(self.hass, user_input)
        except AuthenticationError:
            errors["base"] = "invalid_auth"
        except ConnectTimeout:
            errors["base"] = "cannot_connect"
        except SSLException:
            errors["base"] = "ssl_error"
        except requests.exceptions.ConnectionError:
            errors["base"] = "unknown_error"

        self.context["original_user_input"] = user_input.copy()
        return await self.async_step_selection(proxmox=proxmox)

    async def async_step_selection(
        self,
        user_input: dict[str, Any] | None = None,
        proxmox: ProxmoxAPI | None = None,
    ) -> ConfigFlowResult:
        """Handle the selection step."""
        if user_input is not None:
            user_input.update(self.context["original_user_input"])
            return self.async_create_entry(
                title=DOMAIN,
                data={
                    CONF_HOST: user_input[CONF_HOST],
                    CONF_PORT: user_input[CONF_PORT],
                    CONF_USERNAME: user_input[CONF_USERNAME],
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                    CONF_REALM: user_input[CONF_REALM],
                    CONF_VERIFY_SSL: user_input[CONF_VERIFY_SSL],
                    CONF_NODE: user_input[CONF_NODE],
                },
                options={
                    CONF_VMS: user_input.get(CONF_VMS, []),
                    CONF_CONTAINERS: user_input.get(CONF_CONTAINERS, []),
                },
            )

        context = self.context["original_user_input"]
        if proxmox is None:
            raise HomeAssistantError("Proxmox client not available")

        vms = await self.hass.async_add_executor_job(
            proxmox.nodes(context[CONF_NODE]).qemu.get
        )
        options_vm = [
            SelectOptionDict(
                value=str(vm["vmid"]),
                label=vm["name"],
            )
            for vm in vms
        ]

        containers = await self.hass.async_add_executor_job(
            proxmox.nodes(context[CONF_NODE]).lxc.get
        )
        options_container = [
            SelectOptionDict(
                value=str(container["vmid"]),
                label=container["name"],
            )
            for container in containers
        ]

        return self.async_show_form(
            step_id="selection",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_VMS): SelectSelector(
                        SelectSelectorConfig(
                            options=options_vm,
                            multiple=True,
                            sort=True,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Optional(CONF_CONTAINERS): SelectSelector(
                        SelectSelectorConfig(
                            options=options_container,
                            multiple=True,
                            sort=True,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class SSLException(HomeAssistantError):
    """Error to indicate there is an SSL error."""


class UnknownError(HomeAssistantError):
    """Error to indicate there is an unknown error."""
