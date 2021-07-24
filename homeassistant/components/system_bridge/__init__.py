"""The System Bridge integration."""
from __future__ import annotations

import logging
import shlex

import async_timeout
from systembridge import Bridge
from systembridge.client import BridgeClient
from systembridge.exceptions import BridgeAuthenticationException
from systembridge.objects.command.response import CommandResponse
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_API_KEY,
    CONF_COMMAND,
    CONF_HOST,
    CONF_PATH,
    CONF_PORT,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import (
    aiohttp_client,
    config_validation as cv,
    device_registry as dr,
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BRIDGE_CONNECTION_ERRORS, DOMAIN
from .coordinator import SystemBridgeDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["binary_sensor", "sensor"]

CONF_ARGUMENTS = "arguments"
CONF_BRIDGE = "bridge"
CONF_WAIT = "wait"

SERVICE_SEND_COMMAND = "send_command"
SERVICE_SEND_COMMAND_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_BRIDGE): cv.string,
        vol.Required(CONF_COMMAND): cv.string,
        vol.Optional(CONF_ARGUMENTS, []): cv.string,
    }
)
SERVICE_OPEN = "open"
SERVICE_OPEN_SCHEMA = vol.Schema(
    {vol.Required(CONF_BRIDGE): cv.string, vol.Required(CONF_PATH): cv.string}
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up System Bridge from a config entry."""

    client = Bridge(
        BridgeClient(aiohttp_client.async_get_clientsession(hass)),
        f"http://{entry.data[CONF_HOST]}:{entry.data[CONF_PORT]}",
        entry.data[CONF_API_KEY],
    )

    try:
        async with async_timeout.timeout(60):
            client.async_get_information(),
    except BridgeAuthenticationException as exception:
        raise ConfigEntryAuthFailed from exception
    except BRIDGE_CONNECTION_ERRORS as exception:
        raise ConfigEntryNotReady("Could not connect to System Bridge.") from exception

    coordinator = SystemBridgeDataUpdateCoordinator(hass, _LOGGER, entry=entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    if hass.services.has_service(DOMAIN, SERVICE_SEND_COMMAND):
        return True

    async def handle_send_command(call):
        """Handle the send_command service call."""
        device_registry = dr.async_get(hass)
        device_id = call.data[CONF_BRIDGE]
        device_entry = device_registry.async_get(device_id)
        if device_entry is None:
            _LOGGER.warning("Missing device: %s", device_id)
            return

        command = call.data[CONF_COMMAND]
        arguments = shlex.split(call.data.get(CONF_ARGUMENTS, ""))

        entry_id = next(
            entry.entry_id
            for entry in hass.config_entries.async_entries(DOMAIN)
            if entry.entry_id in device_entry.config_entries
        )
        coordinator: SystemBridgeDataUpdateCoordinator = hass.data[DOMAIN][entry_id]
        bridge: Bridge = coordinator.data

        _LOGGER.debug(
            "Command payload: %s",
            {CONF_COMMAND: command, CONF_ARGUMENTS: arguments, CONF_WAIT: False},
        )
        try:
            response: CommandResponse = await bridge.async_send_command(
                {CONF_COMMAND: command, CONF_ARGUMENTS: arguments, CONF_WAIT: False}
            )
            if response.success:
                _LOGGER.debug(
                    "Sent command. Response message was: %s", response.message
                )
            else:
                _LOGGER.warning(
                    "Error sending command. Response message was: %s", response.message
                )
        except (BridgeAuthenticationException, *BRIDGE_CONNECTION_ERRORS) as exception:
            _LOGGER.warning("Error sending command. Error was: %s", exception)

    async def handle_open(call):
        """Handle the open service call."""
        device_registry = dr.async_get(hass)
        device_id = call.data[CONF_BRIDGE]
        device_entry = device_registry.async_get(device_id)
        if device_entry is None:
            _LOGGER.warning("Missing device: %s", device_id)
            return

        path = call.data[CONF_PATH]

        entry_id = next(
            entry.entry_id
            for entry in hass.config_entries.async_entries(DOMAIN)
            if entry.entry_id in device_entry.config_entries
        )
        coordinator: SystemBridgeDataUpdateCoordinator = hass.data[DOMAIN][entry_id]
        bridge: Bridge = coordinator.data

        _LOGGER.debug("Open payload: %s", {CONF_PATH: path})
        try:
            await bridge.async_open({CONF_PATH: path})
            _LOGGER.debug("Sent open request")
        except (BridgeAuthenticationException, *BRIDGE_CONNECTION_ERRORS) as exception:
            _LOGGER.warning("Error sending. Error was: %s", exception)

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_COMMAND,
        handle_send_command,
        schema=SERVICE_SEND_COMMAND_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_OPEN,
        handle_open,
        schema=SERVICE_OPEN_SCHEMA,
    )

    # Reload entry when its updated.
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: SystemBridgeDataUpdateCoordinator = hass.data[DOMAIN][
            entry.entry_id
        ]

        # Ensure disconnected and cleanup stop sub
        await coordinator.bridge.disconnect()
        if coordinator.unsub:
            coordinator.unsub()

        del hass.data[DOMAIN][entry.entry_id]

    if not hass.data[DOMAIN]:
        hass.services.async_remove(DOMAIN, SERVICE_SEND_COMMAND)
        hass.services.async_remove(DOMAIN, SERVICE_OPEN)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when it changed."""
    await hass.config_entries.async_reload(entry.entry_id)


class SystemBridgeEntity(CoordinatorEntity):
    """Defines a base System Bridge entity."""

    def __init__(
        self,
        coordinator: SystemBridgeDataUpdateCoordinator,
        bridge: Bridge,
        key: str,
        name: str,
        icon: str | None,
        enabled_by_default: bool,
    ) -> None:
        """Initialize the System Bridge entity."""
        super().__init__(coordinator)
        self._key = f"{bridge.os.hostname}_{key}"
        self._name = f"{bridge.os.hostname} {name}"
        self._icon = icon
        self._enabled_default = enabled_by_default
        self._hostname = bridge.os.hostname
        self._default_interface = bridge.network.interfaces[
            bridge.network.interfaceDefault
        ]
        self._manufacturer = bridge.system.system.manufacturer
        self._model = bridge.system.system.model
        self._version = bridge.system.system.version

    @property
    def unique_id(self) -> str:
        """Return the unique ID for this entity."""
        return self._key

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def icon(self) -> str | None:
        """Return the mdi icon of the entity."""
        return self._icon

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added to the entity registry."""
        return self._enabled_default


class SystemBridgeDeviceEntity(SystemBridgeEntity):
    """Defines a System Bridge device entity."""

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this System Bridge instance."""
        return {
            "connections": {
                (dr.CONNECTION_NETWORK_MAC, self._default_interface["mac"])
            },
            "manufacturer": self._manufacturer,
            "model": self._model,
            "name": self._hostname,
            "sw_version": self._version,
        }
