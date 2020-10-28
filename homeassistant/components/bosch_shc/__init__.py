"""The Bosch Smart Home Controller integration."""
import asyncio
import logging

from boschshcpy import SHCSession

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    EVENT_HOMEASSISTANT_START,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

from .const import CONF_SSL_CERTIFICATE, CONF_SSL_KEY, DOMAIN

PLATFORMS = [
    "binary_sensor",
]

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Bosch SHC component."""
    hass.data.setdefault(DOMAIN, {})
    conf = config.get(DOMAIN)

    if not conf:
        return True

    configured_hosts = {
        entry.data.get(CONF_HOST) for entry in hass.config_entries.async_entries(DOMAIN)
    }

    if conf[CONF_HOST] in configured_hosts:
        return True

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_IMPORT}, data=conf
        )
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Bosch SHC from a config entry."""
    data = entry.data

    session = await hass.async_add_executor_job(
        SHCSession,
        data[CONF_HOST],
        data[CONF_SSL_CERTIFICATE],
        data[CONF_SSL_KEY],
    )

    shc_info = session.information
    if shc_info is None:
        _LOGGER.warning("Unable to connect to Bosch Smart Home Controller API")
        raise ConfigEntryNotReady
    if shc_info.updateState.name == "UPDATE_AVAILABLE":
        _LOGGER.warning("Please check for software updates in the Bosch Smart Home App")

    hass.data[DOMAIN][entry.entry_id] = session

    device_registry = await dr.async_get_registry(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, dr.format_mac(shc_info.macAddress))},
        manufacturer="Bosch",
        name=entry.title,
        model="SmartHomeController",
        sw_version=shc_info.version,
    )

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    async def stop_polling(event):
        """Stop polling service."""
        await hass.async_add_executor_job(session.stop_polling)

    async def start_polling(event):
        """Start polling service."""
        await hass.async_add_executor_job(session.start_polling)
        session.reset_connection_listener = hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STOP, stop_polling
        )

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, start_polling)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    session: SHCSession = hass.data[DOMAIN][entry.entry_id]
    if session.reset_connection_listener is not None:
        session.reset_connection_listener()
        _LOGGER.debug("Stopping polling service of SHC")
        await hass.async_add_executor_job(session.stop_polling)

    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
